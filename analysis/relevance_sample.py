"""관련성 라벨링용 무작위 샘플을 뽑는다.

실행: 프로젝트 루트에서 `python analysis/relevance_sample.py`
입력: data/processed/brand_news_filtered.csv
출력: data/processed/relevance_sample.csv (등급 열은 비워 둠)
재현을 위해 random_state를 고정한다.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "brand_news_filtered.csv"
DST = ROOT / "data" / "processed" / "relevance_sample.csv"
N = 30
SEED = 42


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig")
    sample = df.sample(n=N, random_state=SEED).reset_index()
    sample = sample.rename(columns={"index": "원래번호"})
    sample["원래번호"] = sample["원래번호"] + 1
    sample["등급"] = ""
    sample["메모"] = ""
    sample.to_csv(DST, index=False, encoding="utf-8-sig")
    print(f"샘플 {len(sample)}건 저장: {DST.relative_to(ROOT)} (seed={SEED})")
    print(sample["브랜드"].value_counts().to_string())


if __name__ == "__main__":
    main()
