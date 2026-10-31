"""브랜드별 네이버 뉴스 검색 (최신순 50건).

실행: 프로젝트 루트에서 `python analysis/brand_news_search.py`
인증값은 루트의 api_keys.env에서 읽고, 출력하지 않는다.
응답 원본은 data/raw/ 아래에 브랜드별로 저장한다.
"""

import json
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "api_keys.env")

CLIENT_ID = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
NEWS_URL = "https://naverapihub.apigw.ntruss.com/search/v1/news"
BRANDS = ["유니클로", "스파오", "탑텐"]
DISPLAY = 50
TIMEOUT = 10
RAW_DIR = ROOT / "data" / "raw"


def clean(text):
    return re.sub(r"<[^>]+>", "", text).replace("&quot;", '"').replace("&amp;", "&")


def fetch(brand):
    res = requests.get(
        NEWS_URL,
        params={"query": brand, "display": DISPLAY, "start": 1, "sort": "date", "format": "json"},
        headers={
            "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
            "X-NCP-APIGW-API-KEY": CLIENT_SECRET,
        },
        timeout=TIMEOUT,
    )
    data = res.json()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"brand_news_{brand}_{stamp}.json"
    raw_path.write_text(json.dumps({"status": res.status_code, "body": data}, ensure_ascii=False, indent=2), encoding="utf-8")
    return res.status_code, data, raw_path


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("api_keys.env의 NAVER_API_HUB_CLIENT_ID 또는 NAVER_API_HUB_CLIENT_SECRET이 비어 있습니다. 호출을 중단합니다.")
        return

    for brand in BRANDS:
        status, data, raw_path = fetch(brand)
        print(f"\n===== {brand} | HTTP {status} | total={data.get('total')} | 원본: {raw_path.relative_to(ROOT)} =====")
        if status != 200:
            print(f"오류: {data}")
            continue
        for i, it in enumerate(data.get("items", []), 1):
            date = parsedate_to_datetime(it["pubDate"]).strftime("%Y-%m-%d %H:%M")
            print(f"{i:>2}. [{date}] {clean(it['title'])}")
            print(f"    {it['originallink'] or it['link']}")


if __name__ == "__main__":
    main()
