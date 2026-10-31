"""브랜드별·주제별 주요 키워드를 BoW와 TF-IDF로 추출하고 워드클라우드를 만든다.

실행: 프로젝트 루트에서 `python analysis/keyword_bow_tfidf.py`
입력: data/processed/brand_news_topic.csv (제목·요약·브랜드·주제)
출력:
  outputs/tables/keywords_bow_tfidf.csv     방식별 상위 키워드 표
  outputs/figures/wordcloud_{브랜드}.png    BoW/TF-IDF × 전체·주제별 워드클라우드

처리 방식
- 형태소 분석(kiwipiepy)으로 일반명사(NNG)와 고유명사(NNP)만 쓴다. 2글자 미만은 뺀다.
- 불용어와 해당 브랜드명은 제외한다. 다른 브랜드명은 남긴다(비교 대상이므로).
- BoW: 문서 집합 안에서 단어 등장 횟수 합계로 순위를 매긴다.
- TF-IDF: 브랜드 단위(3문서)와 브랜드×주제 단위(문서 집합)로 따로 계산해서,
  여러 문서에 흔한 단어는 낮추고 그 문서에서 특징적인 단어를 올린다.
  단위가 작으면 가중치가 0이 되는 단어가 많으므로 0점은 표에서 뺀다.
"""

import os
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from kiwipiepy import Kiwi
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud

matplotlib.use("Agg")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "processed" / "brand_news_topic.csv"
TABLE_DIR = ROOT / "outputs" / "tables"
FIG_DIR = ROOT / "outputs" / "figures"
FONT = r"C:\Windows\Fonts\malgun.ttf"

BRANDS = ["유니클로", "스파오", "탑텐"]
TOPICS = ["제품 출시", "협업", "할인·행사", "실적·사업", "기타"]
TOP_N = 15

STOPWORDS = {
    "기자", "사진", "제공", "관련", "대표", "이번", "올해", "지난", "대한", "통해", "위해",
    "현재", "주요", "이상", "경우", "대비", "이후", "가능", "것", "수", "때", "명", "회사",
    "브랜드", "오전", "오후", "이날", "동안", "지난해", "지난달", "다음", "매장", "고객",
    "시장", "사업", "기준", "전체", "포함", "정도", "지원", "확대", "진행", "위원", "기업",
    "무료", "정상", "에서", "하기", "중인", "고객들", "그룹", "연합", "뉴스", "사이",
    # 회사명: 모기업·유통사·경쟁사 이름은 주제 단어가 아니라 노이즈로 본다
    "이랜드", "이랜드월드", "신성통상", "무신사", "패스트리테일링", "에프알엘", "삼성물산",
    "롯데", "신세계", "에잇세컨즈",
}
SPAM_TOKENS = {"http", "https", "www", "com", "co", "kr"}


def load_kiwi():
    return Kiwi()


def tokenize(kiwi, text, own_brand):
    tokens = []
    for tok in kiwi.tokenize(str(text)):
        if tok.tag not in ("NNG", "NNP"):
            continue
        form = tok.form
        if len(form) < 2 or form in STOPWORDS or form in SPAM_TOKENS or own_brand in form:
            continue
        tokens.append(form)
    return tokens


def top_bow(tokens, n=TOP_N):
    return Counter(tokens).most_common(n)


def top_tfidf(docs, labels, n=TOP_N):
    """docs: 토큰 리스트들의 리스트, labels: 각 문서의 이름. 문서별 상위 n개를 반환."""
    vec = TfidfVectorizer(analyzer=lambda x: x, min_df=1)
    matrix = vec.fit_transform(docs)
    vocab = vec.get_feature_names_out()
    result = {}
    for i, label in enumerate(labels):
        row = matrix[i].toarray().ravel()
        order = row.argsort()[::-1][:n]
        result[label] = [(vocab[j], round(float(row[j]), 4)) for j in order if row[j] > 0]
    return result


def wordcloud_image(freq, title, ax):
    ax.axis("off")
    ax.set_title(title, fontsize=11)
    if not freq:
        ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center", fontsize=12)
        return
    wc = WordCloud(
        font_path=FONT, width=600, height=400, background_color="white",
        colormap="viridis", prefer_horizontal=0.9,
    ).generate_from_frequencies(dict(freq))
    ax.imshow(wc, interpolation="bilinear")


def main():
    if not os.path.exists(FONT):
        print(f"한글 폰트가 없습니다: {FONT}")
        return

    df = pd.read_csv(SRC, encoding="utf-8-sig")
    kiwi = load_kiwi()

    # 문서 단위: 브랜드×주제 15칸, 브랜드 3칸
    cell_tokens = {}
    brand_tokens = {}
    for brand in BRANDS:
        sub = df[df["브랜드"] == brand]
        brand_tokens[brand] = []
        for _, r in sub.iterrows():
            toks = tokenize(kiwi, f"{r['제목']} {r['요약']}", brand)
            brand_tokens[brand].extend(toks)
            cell_tokens.setdefault((brand, r["주제"]), []).extend(toks)

    # TF-IDF는 문서 집합에 따라 값이 달라지므로 단위별로 따로 계산
    cell_keys = [(b, t) for b in BRANDS for t in TOPICS if (b, t) in cell_tokens]
    cell_tfidf = top_tfidf([cell_tokens[k] for k in cell_keys], [f"{b}|{t}" for b, t in cell_keys])
    brand_tfidf = top_tfidf([brand_tokens[b] for b in BRANDS], BRANDS)

    rows = []
    for brand in BRANDS:
        rows += [
            {"브랜드": brand, "주제": "전체", "방식": "BoW", "순위": i + 1, "키워드": w, "값": c}
            for i, (w, c) in enumerate(top_bow(brand_tokens[brand]))
        ]
        rows += [
            {"브랜드": brand, "주제": "전체", "방식": "TF-IDF", "순위": i + 1, "키워드": w, "값": s}
            for i, (w, s) in enumerate(brand_tfidf.get(brand, []))
        ]
    for (brand, topic) in cell_keys:
        rows += [
            {"브랜드": brand, "주제": topic, "방식": "BoW", "순위": i + 1, "키워드": w, "값": c}
            for i, (w, c) in enumerate(top_bow(cell_tokens[(brand, topic)]))
        ]
        rows += [
            {"브랜드": brand, "주제": topic, "방식": "TF-IDF", "순위": i + 1, "키워드": w, "값": s}
            for i, (w, s) in enumerate(cell_tfidf.get(f"{brand}|{topic}", []))
        ]

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = pd.DataFrame(rows)
    out.to_csv(TABLE_DIR / "keywords_bow_tfidf.csv", index=False, encoding="utf-8-sig")

    # 워드클라우드: 브랜드별 한 장. 1행 BoW, 2행 TF-IDF, 열은 전체 + 주제별
    for brand in BRANDS:
        fig, axes = plt.subplots(2, 1 + len(TOPICS), figsize=(3.2 * (1 + len(TOPICS)), 6.5))
        cols = [("전체", None)] + [(t, t) for t in TOPICS]
        for c, (label, topic) in enumerate(cols):
            if topic is None:
                bow = top_bow(brand_tokens[brand], 50)
                tfidf = brand_tfidf.get(brand, [])
            else:
                bow = top_bow(cell_tokens.get((brand, topic), []), 50)
                tfidf = cell_tfidf.get(f"{brand}|{topic}", [])
            wordcloud_image(bow, f"{brand} · {label}\nBoW", axes[0][c])
            wordcloud_image(tfidf, f"{brand} · {label}\nTF-IDF", axes[1][c])
        fig.tight_layout()
        fig.savefig(FIG_DIR / f"wordcloud_{brand}.png", dpi=130)
        plt.close(fig)

    print(f"저장: {(TABLE_DIR / 'keywords_bow_tfidf.csv').relative_to(ROOT)}")
    print(f"저장: 워드클라우드 {len(BRANDS)}장 -> {FIG_DIR.relative_to(ROOT)}")
    print(out[(out["주제"] == "전체") & (out["순위"] <= 5)].to_string(index=False))


if __name__ == "__main__":
    main()
