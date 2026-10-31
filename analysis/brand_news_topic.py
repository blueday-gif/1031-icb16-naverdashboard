"""정제된 브랜드 뉴스를 주제별로 분류한다.

실행: 프로젝트 루트에서 `python analysis/brand_news_topic.py`
입력: data/processed/brand_news_filtered.csv
출력: data/processed/brand_news_topic.csv (주제 열 추가)

분류 규칙 (위에서부터 먼저 맞는 항목 하나를 주제로 쓴다)
1. 할인·행사: 할인, 세일, 행사, 팝업, 쿠폰, 축제, 프로모션, 텐텐데이
2. 협업: 협업, 콜라보, 컬래버, 캐릭터 IP
3. 제품 출시: 출시, 선보, 신제품, 신상, 론칭, 발매, 컬렉션, 공개
4. 실적·사업: 매출, 실적, 성장, 출점, 인수, 개점, 오픈, 진출, 투자, 가격 인상
5. 기타: 위에 해당하지 않음

키워드 매칭은 제목과 요약을 함께 본다. 자동 분류이므로 결과는 샘플 검토가 필요하다.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "brand_news_filtered.csv"
DST = ROOT / "data" / "processed" / "brand_news_topic.csv"

RULES = [
    ("할인·행사", ["할인", "세일", "행사", "팝업", "쿠폰", "축제", "프로모션", "텐텐데이", "최대 50%"]),
    ("협업", ["협업", "콜라보", "컬래버", "캐릭터 IP", "IP 협업", "손잡", "후원"]),
    ("제품 출시", ["출시", "선보", "신제품", "신상", "론칭", "발매", "컬렉션", "공개", "캡슐", "내놓"]),
    ("실적·사업", ["매출", "실적", "성장", "출점", "인수", "개점", "오픈", "진출", "투자", "가격 인상"]),
]
OTHER = "기타"


def classify(title, summary):
    text = f"{title} {summary}"
    for label, keywords in RULES:
        if any(k in text for k in keywords):
            return label
    return OTHER


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig")
    df["주제"] = [classify(t, s) for t, s in zip(df["제목"], df["요약"])]
    df.to_csv(DST, index=False, encoding="utf-8-sig")

    order = [label for label, _ in RULES] + [OTHER]
    table = pd.crosstab(df["브랜드"], df["주제"]).reindex(columns=order, fill_value=0)
    table["합계"] = table.sum(axis=1)
    print(table.to_string())
    print(f"\n저장: {DST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
