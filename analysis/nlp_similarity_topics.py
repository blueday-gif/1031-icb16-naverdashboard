"""브랜드×주제 칸의 유사도(코사인)와 NMF 토픽 모델링을 계산한다.

실행: 프로젝트 루트에서 `python analysis/nlp_similarity_topics.py`
입력: data/processed/brand_news_topic.csv
출력:
  outputs/tables/cell_cosine_similarity.csv  브랜드×주제 칸 간 코사인 유사도
  outputs/tables/nmf_topics.csv              NMF 토픽별 상위 단어
  outputs/tables/nmf_vs_rule_topic.csv       NMF 토픽과 규칙 기반 주제의 교차표

개념
- 코사인 유사도: 두 문서의 TF-IDF 벡터 사이 각도의 코사인. 1에 가까울수록 단어 구성이 비슷하다.
- NMF(비음수 행렬 분해): 기사×단어 TF-IDF 행렬을 (기사×토픽)과 (토픽×단어) 두 행렬로 나눈다.
  토픽별 가중치가 큰 단어를 보면 기사들이 묶인 주제를 해석할 수 있다. 토픽 개수는 미리 정해야 한다.
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).resolve().parent))
from keyword_bow_tfidf import BRANDS, TOPICS, load_kiwi, tokenize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "brand_news_topic.csv"
TABLE_DIR = ROOT / "outputs" / "tables"
N_TOPICS = 5
TOP_WORDS = 8
SEED = 42


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig").reset_index(drop=True)
    kiwi = load_kiwi()
    df["토큰"] = [
        tokenize(kiwi, f"{r['제목']} {r['요약']}", r["브랜드"]) for _, r in df.iterrows()
    ]
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 브랜드×주제 칸 간 코사인 유사도
    cells = (
        df.groupby(["브랜드", "주제"])["토큰"]
        .apply(lambda s: [w for toks in s for w in toks])
        .reset_index()
    )
    cells["칸"] = cells["브랜드"] + "|" + cells["주제"]
    cell_vec = TfidfVectorizer(analyzer=lambda x: x)
    cell_mat = cell_vec.fit_transform(cells["토큰"])
    sim = pd.DataFrame(
        cosine_similarity(cell_mat), index=cells["칸"], columns=cells["칸"]
    ).round(3)
    sim.to_csv(TABLE_DIR / "cell_cosine_similarity.csv", encoding="utf-8-sig")

    pairs = []
    names = list(sim.index)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs.append((names[i], names[j], sim.iloc[i, j]))
    pairs.sort(key=lambda x: -x[2])
    print("=== 칸 간 코사인 유사도 상위 10쌍 ===")
    for a, b, s in pairs[:10]:
        print(f"  {s:.3f}  {a}  <->  {b}")
    print("\n=== 칸 간 코사인 유사도 하위 5쌍 ===")
    for a, b, s in pairs[-5:]:
        print(f"  {s:.3f}  {a}  <->  {b}")

    # 2) 기사 단위 NMF 토픽 모델링
    docs = df["토큰"].apply(lambda t: " ".join(t))
    vec = TfidfVectorizer(token_pattern=r"(?u)\S+", min_df=2)
    X = vec.fit_transform(docs)
    vocab = vec.get_feature_names_out()
    nmf = NMF(n_components=N_TOPICS, random_state=SEED, init="nndsvda", max_iter=500)
    W = nmf.fit_transform(X)
    H = nmf.components_

    topic_rows = []
    for k in range(N_TOPICS):
        top_idx = H[k].argsort()[::-1][:TOP_WORDS]
        words = [vocab[i] for i in top_idx]
        topic_rows.append({"토픽": f"T{k + 1}", "상위단어": ", ".join(words)})
        print(f"T{k + 1}: {', '.join(words)}")
    pd.DataFrame(topic_rows).to_csv(TABLE_DIR / "nmf_topics.csv", index=False, encoding="utf-8-sig")

    # 3) 기사별 대표 토픽과 규칙 기반 주제 비교
    df["NMF토픽"] = [f"T{k + 1}" for k in W.argmax(axis=1)]
    cross = pd.crosstab(df["NMF토픽"], df["주제"]).reindex(columns=TOPICS, fill_value=0)
    cross = cross.loc[:, [c for c in cross.columns if cross[c].sum() > 0]]
    cross.to_csv(TABLE_DIR / "nmf_vs_rule_topic.csv", encoding="utf-8-sig")
    print("\n=== NMF 토픽 × 규칙 기반 주제 (기사 수) ===")
    print(cross.to_string())

    brand_cross = pd.crosstab(df["NMF토픽"], df["브랜드"]).reindex(columns=BRANDS, fill_value=0)
    print("\n=== NMF 토픽 × 브랜드 (기사 수) ===")
    print(brand_cross.to_string())

    # NMF 재현성 참고: 토픽별 기사 가중치 합
    print("\n토픽별 기사 가중치 합:", np.round(W.sum(axis=0), 2).tolist())
    print(f"\n저장: {TABLE_DIR.relative_to(ROOT)} 아래 CSV 3개")


if __name__ == "__main__":
    main()
