"""브랜드 뉴스·키워드·검색 추이 분석 결과를 한 화면에 보여주는 Streamlit 대시보드.

실행: 프로젝트 루트에서 `py -m streamlit run analysis/dashboard.py`
입력: 앞선 분석 스크립트가 만든 파일만 읽는다 (새로 API를 호출하지 않는다).
  data/processed/brand_news_topic.csv
  data/processed/search_trend_monthly.csv
  data/processed/search_trend_segment.csv
  outputs/tables/keywords_bow_tfidf.csv
  outputs/tables/cell_cosine_similarity.csv
  outputs/tables/nmf_topics.csv
  outputs/tables/nmf_vs_rule_topic.csv
  outputs/figures/wordcloud_{브랜드}.png
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
TABLES = ROOT / "outputs" / "tables"
FIGS = ROOT / "outputs" / "figures"

BRANDS = ["유니클로", "스파오", "탑텐"]
TOPICS = ["제품 출시", "협업", "할인·행사", "실적·사업", "기타"]

st.set_page_config(page_title="브랜드 분석 대시보드", layout="wide")


@st.cache_data
def load_news():
    return pd.read_csv(PROC / "brand_news_topic.csv", encoding="utf-8-sig")


@st.cache_data
def load_keywords():
    return pd.read_csv(TABLES / "keywords_bow_tfidf.csv", encoding="utf-8-sig")


@st.cache_data
def load_monthly():
    return pd.read_csv(PROC / "search_trend_monthly.csv", encoding="utf-8-sig")


@st.cache_data
def load_segment():
    return pd.read_csv(PROC / "search_trend_segment.csv", encoding="utf-8-sig")


@st.cache_data
def load_similarity():
    return pd.read_csv(TABLES / "cell_cosine_similarity.csv", index_col=0, encoding="utf-8-sig")


@st.cache_data
def load_nmf():
    topics = pd.read_csv(TABLES / "nmf_topics.csv", encoding="utf-8-sig")
    cross = pd.read_csv(TABLES / "nmf_vs_rule_topic.csv", index_col=0, encoding="utf-8-sig")
    return topics, cross


news = load_news()
keywords = load_keywords()
monthly = load_monthly()
segment = load_segment()
sim = load_similarity()
nmf_topics, nmf_cross = load_nmf()

st.title("브랜드 뉴스·검색 추이 분석 대시보드")
st.caption(
    f"뉴스 {len(news)}건 (정제 후) · 검색 추이 {monthly['기간'].min()} ~ {monthly['기간'].max()} · "
    "검색 지수는 요청 안 상대 지수(최대 100)입니다."
)

tab_news, tab_kw, tab_sim, tab_trend, tab_notes = st.tabs(
    ["뉴스 개요", "키워드", "유사도·토픽", "검색 추이", "해석과 한계"]
)

# ── 뉴스 개요 ──────────────────────────────────────────────
with tab_news:
    cols = st.columns(len(BRANDS))
    for col, brand in zip(cols, BRANDS):
        n = int((news["브랜드"] == brand).sum())
        col.metric(f"{brand} 기사 수", n)

    st.subheader("브랜드 × 주제 분포")
    counts = news.groupby(["브랜드", "주제"]).size().reset_index(name="건수")
    chart = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            x=alt.X("브랜드:N", sort=BRANDS),
            y=alt.Y("건수:Q", stack=True),
            color=alt.Color("주제:N", sort=TOPICS),
            tooltip=["브랜드", "주제", "건수"],
        )
        .properties(height=350)
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("기사 목록 (필터)")
    f1, f2 = st.columns(2)
    sel_brand = f1.multiselect("브랜드", BRANDS, default=BRANDS)
    sel_topic = f2.multiselect("주제", TOPICS, default=TOPICS)
    view = news[news["브랜드"].isin(sel_brand) & news["주제"].isin(sel_topic)][
        ["브랜드", "주제", "날짜", "제목", "원문링크"]
    ]
    st.caption(f"{len(view)}건 표시")
    st.dataframe(view, use_container_width=True, hide_index=True)

# ── 키워드 ─────────────────────────────────────────────────
with tab_kw:
    st.subheader("워드클라우드 (BoW 1행, TF-IDF 2행)")
    brand_pick = st.selectbox("브랜드 선택", BRANDS, key="kw_brand")
    img = FIGS / f"wordcloud_{brand_pick}.png"
    if img.exists():
        st.image(str(img), use_container_width=True)
    else:
        st.warning(f"워드클라우드 파일이 없습니다: {img.name}")

    st.subheader("상위 키워드 비교 (BoW vs TF-IDF)")
    k1, k2 = st.columns(2)
    k_brand = k1.selectbox("브랜드", BRANDS, key="kw_brand2")
    k_topic = k2.selectbox("주제", ["전체"] + TOPICS, key="kw_topic")
    sub = keywords[(keywords["브랜드"] == k_brand) & (keywords["주제"] == k_topic)]
    if sub.empty:
        st.info("이 조합에는 키워드가 없습니다(기사 없음).")
    else:
        left, right = st.columns(2)
        for col, method in zip((left, right), ["BoW", "TF-IDF"]):
            part = sub[sub["방식"] == method][["순위", "키워드", "값"]]
            col.markdown(f"**{method}**")
            col.dataframe(part, hide_index=True, use_container_width=True)
    st.caption("BoW 값은 등장 횟수, TF-IDF 값은 가중치입니다. 값의 단위가 달라서 두 방식의 숫자를 직접 비교하지 마세요.")

# ── 유사도·토픽 ────────────────────────────────────────────
with tab_sim:
    st.subheader("브랜드×주제 칸 간 코사인 유사도")
    sim_long = sim.reset_index().melt(id_vars=sim.index.name or "index", var_name="칸2", value_name="유사도")
    sim_long = sim_long.rename(columns={sim.index.name or "index": "칸1"})
    heat = (
        alt.Chart(sim_long)
        .mark_rect()
        .encode(
            x=alt.X("칸2:N", sort=list(sim.columns), title=None),
            y=alt.Y("칸1:N", sort=list(sim.index), title=None),
            color=alt.Color("유사도:Q", scale=alt.Scale(scheme="blues", domain=[0, 1])),
            tooltip=["칸1", "칸2", alt.Tooltip("유사도:Q", format=".3f")],
        )
        .properties(height=420)
    )
    st.altair_chart(heat, use_container_width=True)
    st.caption("1에 가까울수록 단어 구성이 비슷합니다. 기사 수가 적은 칸은 값이 불안정할 수 있습니다.")

    st.subheader("NMF 토픽 (기사 묶음을 단어로 해석)")
    st.dataframe(nmf_topics, hide_index=True, use_container_width=True)

    st.subheader("NMF 토픽 × 규칙 기반 주제 (기사 수)")
    st.dataframe(nmf_cross, use_container_width=True)
    st.caption("T2(양말 가격 인상) 기사가 규칙 분류에서 '실적·사업'에 섞인 것이 이 표에서 드러납니다.")

# ── 검색 추이 ──────────────────────────────────────────────
with tab_trend:
    st.subheader("월별 검색 추이 (같은 요청 안 상대 지수)")
    pivot = monthly.pivot(index="기간", columns="브랜드", values="지수")[BRANDS]
    st.line_chart(pivot)

    st.subheader("연령별 상대 비중 (브랜드 안에서의 구성)")
    age = segment[segment["구분종류"] == "연령"]
    age_chart = (
        alt.Chart(age)
        .mark_bar()
        .encode(
            x=alt.X("구분:N", sort=None, title=None),
            y=alt.Y("상대비중:Q", axis=alt.Axis(format=".0%")),
            color="브랜드:N",
            xOffset="브랜드:N",
            tooltip=["브랜드", "구분", alt.Tooltip("상대비중:Q", format=".1%")],
        )
        .properties(height=350)
    )
    st.altair_chart(age_chart, use_container_width=True)

    st.subheader("성별·기기 상대 비중")
    gd = segment[segment["구분종류"].isin(["성별", "기기"])]
    gd_chart = (
        alt.Chart(gd)
        .mark_bar()
        .encode(
            x=alt.X("브랜드:N", sort=BRANDS, title=None),
            y=alt.Y("상대비중:Q", stack="normalize", axis=alt.Axis(format=".0%")),
            color="구분:N",
            column=alt.Column("구분종류:N", title=None),
            tooltip=["브랜드", "구분종류", "구분", alt.Tooltip("상대비중:Q", format=".1%")],
        )
        .properties(width=220, height=300)
    )
    st.altair_chart(gd_chart)

# ── 해석과 한계 ────────────────────────────────────────────
with tab_notes:
    st.markdown(
        """
**뉴스**
- 유니클로 기사는 실적·사업과 협업이 많고, 양말 가격 인상 이슈가 크게 다뤄졌습니다.
- 스파오는 제품 출시(경량패딩, 발열내의)가 많고, 이랜드 소장품 기사가 섞여 있습니다.
- 탑텐은 '텐텐데이' 할인 기사가 대부분입니다. 같은 보도자료가 여러 언론에 실려 중복이 많습니다.

**검색 추이**
- 유니클로가 검색량이 가장 큽니다. 2025년 10~12월과 2026년 5월에 높았습니다.
- 탑텐은 2025년 10월에 뚜렷하게 솟았습니다. 행사 시기와 겹치는 것으로 보이지만 가설입니다.
- 스파오는 2026년 들어 점진적으로 오르고 있고, 연령은 10대 비중이 높습니다.

**한계**
- 뉴스는 검색 API가 준 요약 기준이라 본문 전체를 본 것이 아닙니다.
- 관련성 판정과 주제 분류는 키워드 규칙 기반이라 오분류가 있습니다.
- 검색 지수는 요청마다 상대 지수라서 브랜드 간 비교는 같은 요청 안에서만 유효합니다.
- 연령·성별·기기 비중은 요청을 나눠 받은 근사치입니다.
"""
    )
