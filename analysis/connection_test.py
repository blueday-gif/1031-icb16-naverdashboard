"""NAVER API HUB 기본 연동 테스트.

실행: 프로젝트 루트에서 `python analysis/connection_test.py`
인증값은 루트의 api_keys.env에서 읽고, 출력하지 않는다.
응답 원본은 data/raw/ 아래에 시각을 붙여 저장한다.
"""

import json
import os
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "api_keys.env")

CLIENT_ID = os.getenv("NAVER_API_HUB_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("NAVER_API_HUB_CLIENT_SECRET", "").strip()
BASE_URL = "https://naverapihub.apigw.ntruss.com"
TIMEOUT = 10
RAW_DIR = ROOT / "data" / "raw"


def headers(json_body=False):
    h = {
        "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
        "X-NCP-APIGW-API-KEY": CLIENT_SECRET,
    }
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def save_raw(name, body):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RAW_DIR / f"{name}_{stamp}.json"
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def call(name, method, path, params=None, body=None):
    url = BASE_URL + path
    try:
        if method == "GET":
            res = requests.get(url, params=params, headers=headers(), timeout=TIMEOUT)
        else:
            res = requests.post(url, json=body, headers=headers(True), timeout=TIMEOUT)
    except requests.RequestException as e:
        print(f"[{name}] 요청 실패: {type(e).__name__}")
        return

    try:
        data = res.json()
    except ValueError:
        data = {"raw_text": res.text}

    saved = save_raw(name, {"status": res.status_code, "body": data})
    print(f"[{name}] HTTP {res.status_code} / 원본 저장: {saved.relative_to(ROOT)}")

    if res.status_code == 200:
        items = data.get("items")
        if items is not None:
            print(f"    total={data.get('total')} items={len(items)}")
        elif "results" in data:
            print(f"    results={len(data['results'])}")
        else:
            print(f"    응답 키: {list(data.keys())}")
    else:
        err = data.get("error") or data
        print(f"    오류: {err}")


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("api_keys.env의 NAVER_API_HUB_CLIENT_ID 또는 NAVER_API_HUB_CLIENT_SECRET이 비어 있습니다. 호출을 중단합니다.")
        return

    call("news", "GET", "/search/v1/news",
         params={"query": "제네시스 사모펀드", "display": 5, "start": 1, "sort": "date", "format": "json"})

    call("search_trend", "POST", "/search-trend/v1/search", body={
        "startDate": "2026-01-01",
        "endDate": "2026-09-30",
        "timeUnit": "month",
        "keywordGroups": [{"groupName": "커피", "keywords": ["커피"]}],
    })

    call("shopping_category", "POST", "/shopping/v1/categories", body={
        "startDate": "2026-01-01",
        "endDate": "2026-09-30",
        "timeUnit": "month",
        "category": [{"name": "패션의류", "param": ["50000000"]}],
    })


if __name__ == "__main__":
    main()
