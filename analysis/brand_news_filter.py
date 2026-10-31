"""브랜드 무관 기사를 제외한 정제 CSV를 만든다.

실행: 프로젝트 루트에서 `python analysis/brand_news_filter.py`
입력: data/processed/brand_news_summary.csv (원본 요약, 수정하지 않음)
출력: data/processed/brand_news_filtered.csv

번호는 brand_news_review.py가 붙이는 번호(1부터, CSV 행 순서)와 같다.
중복 제거와 애매한 기사는 이 스크립트에서 다루지 않는다.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "brand_news_summary.csv"
DST = ROOT / "data" / "processed" / "brand_news_filtered.csv"

# 제외 권장 중 확정된 35건 (번호 기준)
EXCLUDE_NO = [
    # 탑텐 검색에 걸린 텐아시아 가수 배너, MAMA 기사
    102, 103, 104, 105, 122, 123, 125, 126, 116,
    # 유니클로 검색에 걸린 무관 기사
    2, 7, 22, 33, 23, 24, 25, 27, 47, 94,
    # 기프티엘 쿠폰 중단 (취급 브랜드 목록)
    32, 36, 37, 40,
    # 런드리고 세탁 보도자료 (수치 인용만)
    31, 34, 38, 42, 43, 44,
    # 스파오 검색에 걸린 무관 기사
    83, 88, 89, 100, 127, 136,
]


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig")
    no = pd.Series(range(1, len(df) + 1), index=df.index)
    excluded = df[no.isin(EXCLUDE_NO)]
    kept = df[~no.isin(EXCLUDE_NO)]

    assert len(excluded) == len(set(EXCLUDE_NO)), "제외 번호와 실제 행 수가 맞지 않습니다."

    kept.to_csv(DST, index=False, encoding="utf-8-sig")
    print(f"원본 {len(df)}건 -> 제외 {len(excluded)}건 -> 정제 {len(kept)}건")
    print(f"저장: {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
