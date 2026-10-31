"""브랜드별 검색 추이(월별·연령별·성별·기기별)를 DataLab 검색 추이 API로 가져와 표와 그래프를 만든다.

실행: 프로젝트 루트에서 `python analysis/search_trend_brands.py`
인증값은 루트의 api_keys.env에서 읽고 출력하지 않는다.

입력 조건
- 기간: 2025-01-01 ~ 2026-09-30 (완성된 월만 사용), 단위: 월(month)
- 비교 대상: 유니클로, 스파오, 탑텐 (한 요청에 3개 그룹을 넣어 같은 기준으로 비교)

중요한 제약 (개념)
- 검색 추이 값(ratio)은 요청 안에서 가장 높은 값을 100으로 맞춘 상대 지수다.
  그래서 요청이 다르면 값을 직접 비교할 수 없다. 같은 요청 안에서만 브랜드끼리 비교한다.
- 연령·성별·기기 구성은 요청을 나눠서 얻기 때문에, 각 요청의 스케일이 달라 엄밀한 비율이 아니다.
  이 스크립트는 브랜드별로 각 구분의 평균 지수를 구하고 구분 내 상대 비중으로 보여준다.
  값의 크기가 아니라 구성의 '모양'을 비교하는 용도로만 쓴다.

출력
  data/processed/search_trend_monthly.csv
  data/processed/search_trend_segment.csv      (연령·성별·기기별 평균 지수와 상대 비중)
  outputs/figures/trend_monthly.png
  outputs/figures/trend_age.png
  outputs/figures/trend_gender_device.png
  data/raw/datalab_*.json                       (요청별 원본 응답)
"""

import json
import os
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv

matplotlib.use("Agg")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "api_keys.env")

CLIENT_ID = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
URL = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
TIMEOUT = 15
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
FIG_DIR = ROOT / "outputs" / "figures"

START, END = "2025-01-01", "2026-09-30"
BRANDS = {"유니클로": ["유니클로"], "스파오": ["스파오"], "탑텐": ["탑텐"]}
AGES = {
    "1": "12세 미만", "2": "12~18세", "3": "19~24세", "4": "25~29세", "5": "30~34세",
    "6": "35~39세", "7": "40~44세", "8": "45~49세", "9": "50~54세", "10": "55~59세", "11": "60세 이상",
}
GENDERS = {"m": "남성", "f": "여성"}
DEVICES = {"pc": "PC", "mo": "모바일"}


def request_trend(name, extra=None):
    """요청 한 번 보내고 원본을 저장한다. 결과는 {브랜드: [(기간, 지수)]} 형태로 돌려준다."""
    body = {
        "startDate": START,
        "endDate": END,
        "timeUnit": "month",
        "keywordGroups": [{"groupName": b, "keywords": kws} for b, kws in BRANDS.items()],
    }
    if extra:
        body.update(extra)
    res = requests.post(
        URL,
        json=body,
        headers={
            "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
            "X-NCP-APIGW-API-KEY": CLIENT_SECRET,
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )
    try:
        data = res.json()
    except ValueError:
        data = {"raw_text": res.text}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = name.replace("|", "_")
    (RAW_DIR / f"datalab_{tag}_{stamp}.json").write_text(
        json.dumps({"request": body, "status": res.status_code, "body": data}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if res.status_code != 200:
        raise RuntimeError(f"[{name}] HTTP {res.status_code}: {data}")

    series = {}
    for r in data.get("results", []):
        series[r["title"]] = [(d["period"], d["ratio"]) for d in r.get("data", [])]
    return series


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("api_keys.env의 인증값이 비어 있습니다. 호출을 중단합니다.")
        return

    # 1) 월별 추이: 3개 브랜드를 한 요청으로 비교
    monthly_series = request_trend("monthly")
    monthly = []
    for brand, points in monthly_series.items():
        for period, ratio in points:
            monthly.append({"브랜드": brand, "기간": period, "지수": ratio})
    monthly_df = pd.DataFrame(monthly)
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    monthly_df.to_csv(PROC_DIR / "search_trend_monthly.csv", index=False, encoding="utf-8-sig")

    # 2) 구분별(연령·성별·기기) 평균 지수: 요청을 나눠서 받는다
    seg_rows = []
    for code, label in AGES.items():
        s = request_trend(f"age{code}", {"ages": [code]})
        for brand, points in s.items():
            avg = sum(v for _, v in points) / len(points) if points else 0.0
            seg_rows.append({"구분종류": "연령", "구분": label, "브랜드": brand, "평균지수": round(avg, 2)})
    for code, label in GENDERS.items():
        s = request_trend(f"gender{code}", {"gender": code})
        for brand, points in s.items():
            avg = sum(v for _, v in points) / len(points) if points else 0.0
            seg_rows.append({"구분종류": "성별", "구분": label, "브랜드": brand, "평균지수": round(avg, 2)})
    for code, label in DEVICES.items():
        s = request_trend(f"device{code}", {"device": code})
        for brand, points in s.items():
            avg = sum(v for _, v in points) / len(points) if points else 0.0
            seg_rows.append({"구분종류": "기기", "구분": label, "브랜드": brand, "평균지수": round(avg, 2)})

    seg_df = pd.DataFrame(seg_rows)
    # 구분 종류 안에서 브랜드별 상대 비중 (구분별 합이 1이 되도록)
    seg_df["상대비중"] = seg_df.groupby(["구분종류", "브랜드"])["평균지수"].transform(
        lambda x: x / x.sum() if x.sum() else 0
    ).round(4)
    seg_df.to_csv(PROC_DIR / "search_trend_segment.csv", index=False, encoding="utf-8-sig")

    # 3) 그래프
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5))
    for brand in BRANDS:
        sub = monthly_df[monthly_df["브랜드"] == brand]
        ax.plot(sub["기간"], sub["지수"], marker="o", label=brand)
    ax.set_title("브랜드별 월별 검색 추이 (같은 요청 안의 상대 지수)")
    ax.set_ylabel("지수 (최대 100)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "trend_monthly.png", dpi=130)
    plt.close(fig)

    age_df = seg_df[seg_df["구분종류"] == "연령"].pivot(index="구분", columns="브랜드", values="상대비중")
    age_df = age_df.reindex(list(AGES.values()))
    fig, ax = plt.subplots(figsize=(9, 6))
    im = ax.imshow(age_df.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(age_df.columns)), age_df.columns)
    ax.set_yticks(range(len(age_df.index)), age_df.index)
    for i in range(age_df.shape[0]):
        for j in range(age_df.shape[1]):
            ax.text(j, i, f"{age_df.values[i, j]:.0%}", ha="center", va="center", fontsize=9)
    ax.set_title("연령별 상대 비중 (브랜드별 합 = 100%)")
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "trend_age.png", dpi=130)
    plt.close(fig)

    gd = seg_df[seg_df["구분종류"].isin(["성별", "기기"])]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, kind in zip(axes, ["성별", "기기"]):
        piv = gd[gd["구분종류"] == kind].pivot(index="브랜드", columns="구분", values="상대비중")
        piv.plot(kind="bar", stacked=True, ax=ax, rot=0)
        ax.set_title(f"{kind}별 상대 비중")
        ax.set_ylabel("비중")
        ax.legend(title=kind)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "trend_gender_device.png", dpi=130)
    plt.close(fig)

    print("월별 요약(평균 지수):")
    print(monthly_df.groupby("브랜드")["지수"].agg(["mean", "max", "min"]).round(1).to_string())
    print("\n연령별 상대 비중:")
    print(age_df.round(3).to_string())
    print("\n성별·기기 상대 비중:")
    print(gd.pivot_table(index=["구분종류", "구분"], columns="브랜드", values="상대비중").round(3).to_string())
    print("\n저장: data/processed/search_trend_*.csv, outputs/figures/trend_*.png")


if __name__ == "__main__":
    main()
