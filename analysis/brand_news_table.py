"""브랜드별 뉴스 원본 JSON을 표(CSV, Markdown)로 정리한다.

실행: 프로젝트 루트에서 `python analysis/brand_news_table.py`
입력: data/raw/brand_news_{브랜드}_*.json 중 가장 최근 파일
출력: data/processed/brand_news_summary.csv, outputs/tables/brand_news_summary.md
"""

import csv
import json
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR = ROOT / "outputs" / "tables"
BRANDS = ["유니클로", "스파오", "탑텐"]


def clean(text):
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()


def latest_file(brand):
    files = sorted(RAW_DIR.glob(f"brand_news_{brand}_*.json"))
    return files[-1] if files else None


def load_rows(brand):
    path = latest_file(brand)
    if path is None:
        print(f"[{brand}] 원본 파일이 없습니다.")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for it in data["body"].get("items", []):
        dt = parsedate_to_datetime(it["pubDate"]).strftime("%Y-%m-%d %H:%M")
        rows.append({
            "브랜드": brand,
            "제목": clean(it["title"]),
            "요약": clean(it["description"]),
            "날짜": dt,
            "원문링크": it["originallink"] or it["link"],
        })
    print(f"[{brand}] {path.name} -> {len(rows)}건")
    return rows


def to_markdown(df):
    lines = ["| 번호 | 제목 | 요약 | 날짜 | 원문링크 |", "|---|---|---|---|---|"]
    for i, r in enumerate(df.itertuples(index=False), 1):
        cells = [str(i), r.제목, r.요약, r.날짜, r.원문링크]
        cells = [c.replace("|", "\\|").replace("\n", " ") for c in cells]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    rows = []
    for brand in BRANDS:
        rows.extend(load_rows(brand))
    if not rows:
        return

    df = pd.DataFrame(rows)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "brand_news_summary.csv", index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)

    md_parts = [f"# 브랜드별 네이버 뉴스 요약\n\n생성 시각: {datetime.now():%Y-%m-%d %H:%M}\n"]
    for brand in BRANDS:
        sub = df[df["브랜드"] == brand].reset_index(drop=True)
        md_parts.append(f"\n## {brand} ({len(sub)}건)\n\n" + to_markdown(sub))
    (OUT_DIR / "brand_news_summary.md").write_text("".join(md_parts), encoding="utf-8")

    print(f"저장: {(PROCESSED_DIR / 'brand_news_summary.csv').relative_to(ROOT)}")
    print(f"저장: {(OUT_DIR / 'brand_news_summary.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
