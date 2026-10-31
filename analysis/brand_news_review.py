"""브랜드 뉴스 CSV의 중복 기사와 관련성 판단 대상을 출력한다.

실행: 프로젝트 루트에서 `python analysis/brand_news_review.py`
입력: data/processed/brand_news_summary.csv
출력: 콘솔만 사용한다. 제외 여부는 사람이 판단한다.

관련성 기준(자동 분류)
- 제목에 브랜드명 있음: 관련 가능성 높음
- 제목에는 없고 요약에만 있음: 애매함 (판단 필요)
- 제목과 요약 모두 없음: 관련성 낮음 (검색어 매칭 오류 가능성)
"""

import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "processed" / "brand_news_summary.csv"
BRAND_KEYWORDS = {
    "유니클로": ["유니클로", "UNIQLO"],
    "스파오": ["스파오", "SPAO"],
    "탑텐": ["탑텐", "TOPTEN", "TOP10"],
}
SIMILAR_TITLE = 0.85


def norm(text):
    return re.sub(r"[\s\W_]+", "", str(text)).lower()


def find_duplicates(df):
    """같은 원문링크이거나 제목이 거의 같은 기사를 묶는다."""
    parent = list(range(len(df)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        parent[root(a)] = root(b)

    titles = [norm(t) for t in df["제목"]]
    links = list(df["원문링크"])
    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            same_link = links[i] == links[j]
            similar = SequenceMatcher(None, titles[i], titles[j]).ratio() >= SIMILAR_TITLE
            if same_link or similar:
                union(i, j)

    groups = {}
    for i in range(len(df)):
        groups.setdefault(root(i), []).append(i)
    return [g for g in groups.values() if len(g) > 1]


def classify(row):
    title = str(row["제목"])
    summary = str(row["요약"])
    brand = row["브랜드"]
    kws = BRAND_KEYWORDS[brand]
    if any(k.lower() in title.lower() for k in kws):
        return "제목 포함"
    if any(k.lower() in summary.lower() for k in kws):
        return "요약만 포함"
    return "미포함"


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    df.insert(0, "번호", range(1, len(df) + 1))
    df["판정"] = df.apply(classify, axis=1)

    print(f"전체 {len(df)}건\n")

    print("=== 1. 중복 기사 그룹 (같은 링크 또는 제목 유사도 {:.0%} 이상) ===".format(SIMILAR_TITLE))
    dup_groups = find_duplicates(df)
    print(f"그룹 {len(dup_groups)}개, 중복 의심 {sum(len(g) for g in dup_groups)}건\n")
    for n, g in enumerate(dup_groups, 1):
        print(f"[그룹 {n}]")
        for i in g:
            r = df.iloc[i]
            print(f"  #{r['번호']:>3} [{r['브랜드']}] {r['날짜']} {r['제목']}")
        print()

    for label in ["미포함", "요약만 포함"]:
        sub = df[df["판정"] == label]
        title = "2. 브랜드 미포함 (관련성 낮음 가능성)" if label == "미포함" else "3. 요약에만 브랜드 언급 (애매함, 판단 필요)"
        print(f"=== {title}: {len(sub)}건 ===")
        for _, r in sub.iterrows():
            print(f"  #{r['번호']:>3} [{r['브랜드']}] {r['날짜']} {r['제목']}")
            if label == "요약만 포함":
                print(f"        요약: {str(r['요약'])[:120]}")
        print()

    print(f"=== 참고: 제목 포함 {int((df['판정'] == '제목 포함').sum())}건은 자동 통과 (제목만으로 주제가 다른 경우는 별도 확인 필요) ===")


if __name__ == "__main__":
    main()
