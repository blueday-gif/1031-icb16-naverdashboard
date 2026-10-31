"""정제 CSV의 브랜드별 기사 수를 목표(50건)까지 채운다.

실행: 프로젝트 루트에서 `python analysis/brand_news_fill.py`
입력: data/processed/brand_news_summary.csv (전체 수집분, 제외 기사 포함)
      data/processed/brand_news_filtered.csv (제외 적용분)
출력: data/processed/brand_news_filtered.csv (50건 맞춤, 덮어씀)
      data/raw/brand_news_fill_{브랜드}_*.json (추가 조회 원본)

중복 기준
- 전체 수집분(제외된 기사 포함)과 원문링크가 같거나 제목이 거의 같으면 추가하지 않는다.
- 이번 실행에서 이미 추가한 기사와도 같은 기준으로 비교한다.
관련성 기준
- 제목에 브랜드명이 있는 기사만 추가한다.
"""

import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "api_keys.env")

CLIENT_ID = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
NEWS_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
TIMEOUT = 10
TARGET = 50
PAGE_SIZE = 100
MAX_START = 301  # 최대 300건까지 조회 (start 1, 101, 201)

SUMMARY = ROOT / "data" / "processed" / "brand_news_summary.csv"
FILTERED = ROOT / "data" / "processed" / "brand_news_filtered.csv"
RAW_DIR = ROOT / "data" / "raw"

BRAND_KEYWORDS = {
    "유니클로": ["유니클로", "UNIQLO"],
    "스파오": ["스파오", "SPAO"],
    "탑텐": ["탑텐", "TOPTEN"],
}
SIMILAR_TITLE = 0.85


def clean(text):
    text = re.sub(r"<[^>]+>", "", str(text))
    return text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()


def norm(text):
    return re.sub(r"[\s\W_]+", "", str(text)).lower()


def is_duplicate(title_norm, link, known_links, known_titles):
    if link in known_links:
        return True
    return any(SequenceMatcher(None, title_norm, t).ratio() >= SIMILAR_TITLE for t in known_titles)


def fetch_page(brand, start):
    res = requests.get(
        NEWS_URL,
        params={"query": brand, "display": PAGE_SIZE, "start": start, "sort": "date", "format": "json"},
        headers={
            "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
            "X-NCP-APIGW-API-KEY": CLIENT_SECRET,
        },
        timeout=TIMEOUT,
    )
    data = res.json()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RAW_DIR / f"brand_news_fill_{brand}_start{start}_{stamp}.json"
    path.write_text(json.dumps({"status": res.status_code, "body": data}, ensure_ascii=False, indent=2), encoding="utf-8")
    return res.status_code, data


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("api_keys.env의 NAVER_API_HUB_CLIENT_ID 또는 NAVER_API_HUB_CLIENT_SECRET이 비어 있습니다. 호출을 중단합니다.")
        return

    summary = pd.read_csv(SUMMARY, encoding="utf-8-sig")
    filtered = pd.read_csv(FILTERED, encoding="utf-8-sig")

    known_links = set(summary["원문링크"])
    known_titles = [norm(t) for t in summary["제목"]]

    new_rows = []
    for brand, keywords in BRAND_KEYWORDS.items():
        have = int((filtered["브랜드"] == brand).sum())
        need = TARGET - have
        print(f"[{brand}] 현재 {have}건, 추가 필요 {need}건")
        if need <= 0:
            continue

        added = 0
        for start in range(1, MAX_START, PAGE_SIZE):
            if added >= need:
                break
            status, data = fetch_page(brand, start)
            if status != 200:
                print(f"  start={start} HTTP {status}: {data}")
                break
            items = data.get("items", [])
            if not items:
                break
            for it in items:
                if added >= need:
                    break
                title = clean(it["title"])
                if not any(k.lower() in title.lower() for k in keywords):
                    continue
                link = it["originallink"] or it["link"]
                tn = norm(title)
                if is_duplicate(tn, link, known_links, known_titles):
                    continue
                dt = parsedate_to_datetime(it["pubDate"]).strftime("%Y-%m-%d %H:%M")
                new_rows.append({
                    "브랜드": brand,
                    "제목": title,
                    "요약": clean(it["description"]),
                    "날짜": dt,
                    "원문링크": link,
                })
                known_links.add(link)
                known_titles.append(tn)
                added += 1
        print(f"  추가 {added}건 (목표 {need}건)")

    out = pd.concat([filtered, pd.DataFrame(new_rows)], ignore_index=True)
    out.to_csv(FILTERED, index=False, encoding="utf-8-sig")

    counts = out["브랜드"].value_counts().to_dict()
    print(f"\n저장: {FILTERED.relative_to(ROOT)} (총 {len(out)}건)")
    for brand in BRAND_KEYWORDS:
        print(f"  {brand}: {counts.get(brand, 0)}건")


if __name__ == "__main__":
    main()
