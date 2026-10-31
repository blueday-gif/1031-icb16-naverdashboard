"""브랜드 뉴스·키워드·검색 추이 분석 결과를 보고용으로 보여주는 Streamlit 대시보드.

실행: 프로젝트 루트에서 `py -m streamlit run streamlit_app.py`
입력: 앞선 분석 스크립트가 만든 파일만 읽는다 (새로 API를 호출하지 않는다).
  data/processed/brand_news_topic.csv
  data/processed/search_trend_monthly.csv
  data/processed/search_trend_segment.csv
  outputs/tables/keywords_bow_tfidf.csv
  outputs/tables/cell_cosine_similarity.csv
  outputs/tables/nmf_topics.csv
  outputs/tables/nmf_vs_rule_topic.csv
  outputs/figures/wordcloud_{브랜드}.png

디자인 기준은 analysis/ui_ux_rubric.md 를 따른다.
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

# 중성 톤 기본 + 브랜드 고정색 (브랜드 가이드가 없으므로 구분만 되도록 고른 색)
INK = "#1F2933"
MUTED = "#616E7C"
LINE = "#E4E7EB"
BRAND_COLORS = {"유니클로": "#2F3E4E", "스파오": "#B8704F", "탑텐": "#5E8C7A"}
# 주제 색은 브랜드 색과 겹치지 않도록 별도 계열로 둔다
TOPIC_COLORS = {
    "제품 출시": "#7C8DA0",
    "협업": "#A7B4C2",
    "할인·행사": "#D9A441",
    "실적·사업": "#C9D3DD",
    "기타": "#EEF1F4",
}

st.set_page_config(page_title="브랜드 분석 대시보드", layout="wide")

st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 2rem; max-width: 1200px; }}
      h1 {{ font-size: 1.9rem !important; color: {INK}; }}
      h2, h3 {{ color: {INK}; }}
      .lead {{ color: {MUTED}; font-size: 0.95rem; margin-bottom: 0.5rem; }}
      .read-hint {{ color: {MUTED}; font-size: 0.85rem; border-left: 3px solid {LINE};
                   padding-left: 0.6rem; margin: 0.3rem 0 1rem 0; }}
      .finding {{ border: 1px solid {LINE}; border-radius: 8px; padding: 0.9rem 1rem; height: 100%; }}
      .finding .label {{ color: {MUTED}; font-size: 0.8rem; }}
      .finding .value {{ color: {INK}; font-size: 1.15rem; font-weight: 600; margin: 0.2rem 0; }}
      .finding .desc {{ color: {INK}; font-size: 0.9rem; }}
      .source {{ color: {MUTED}; font-size: 0.8rem; margin-top: 2rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def brand_scale():
    return alt.Scale(domain=BRANDS, range=[BRAND_COLORS[b] for b in BRANDS])


def topic_scale():
    return alt.Scale(domain=TOPICS, range=[TOPIC_COLORS[t] for t in TOPICS])


@st.cache_data
def load_news():
    return pd.read_csv(PROC / "brand_news_topic.csv", encoding="utf-8-sig")


@st.cache_data
def load_keywords():
    return pd.read_csv(TABLES / "keywords_bow_tfidf.csv", encoding="utf-8-sig")


@st.cache_data
def load_monthly():
    df = pd.read_csv(PROC / "search_trend_monthly.csv", encoding="utf-8-sig")
    df["기간"] = pd.to_datetime(df["기간"])
    return df


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

# ── 결론 계산 (화면 문구의 숫자는 모두 데이터에서 계산) ───────────
avg_index = monthly.groupby("브랜드")["지수"].mean()
top_topic = {}
for b in BRANDS:
    # '기타'는 분류되지 않은 기사이므로 주요 주제 판단에서 뺀다
    named = news[(news["브랜드"] == b) & (news["주제"] != "기타")]["주제"]
    share = named.value_counts(normalize=True)
    top_topic[b] = (share.index[0], share.iloc[0])
young_share = (
    segment[(segment["구분종류"] == "연령") & (segment["구분"].isin(["12세 미만", "12~18세"]))]
    .groupby("브랜드")["상대비중"].sum()
)
mid_share = (
    segment[(segment["구분종류"] == "연령") & (segment["구분"].isin(["30~34세", "35~39세", "40~44세"]))]
    .groupby("브랜드")["상대비중"].sum()
)

st.title("브랜드 뉴스·검색 추이 분석")
st.markdown(
    '<p class="lead">유니클로·스파오·탑텐을 뉴스 노출과 검색 관심 두 측면에서 비교합니다.</p>',
    unsafe_allow_html=True,
)

# ── 핵심 결론 3개 ──────────────────────────────────────────
st.subheader("핵심 결론")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f"""<div class="finding">
        <div class="label">검색 관심 규모</div>
        <div class="value">유니클로 평균 {avg_index['유니클로']:.0f}</div>
        <div class="desc">스파오 {avg_index['스파오']:.0f}, 탑텐 {avg_index['탑텐']:.0f}.
        유니클로는 세 브랜드 중 검색 관심이 가장 큽니다. (상대 지수, 같은 요청 안 비교)</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c2:
    t_topic, t_share = top_topic["탑텐"]
    s_topic, s_share = top_topic["스파오"]
    st.markdown(
        f"""<div class="finding">
        <div class="label">뉴스에서 주로 다뤄진 내용 (기타 제외 기준)</div>
        <div class="value">탑텐 · {t_topic} {t_share:.0%}</div>
        <div class="desc">스파오는 <b>{s_topic}</b> {s_share:.0%}가 가장 많습니다.
        탑텐 기사는 행사 보도에 집중되어 있습니다.</div>
        </div>""",
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f"""<div class="finding">
        <div class="label">검색 고객층</div>
        <div class="value">스파오 10대 이하 {young_share['스파오']:.0%}</div>
        <div class="desc">탑텐은 30~44세 {mid_share['탑텐']:.0%}, 유니클로는 연령이 고르게 분포합니다.
        연령 구성은 근사치입니다.</div>
        </div>""",
        unsafe_allow_html=True,
    )

tab_news, tab_kw, tab_sim, tab_trend, tab_notes = st.tabs(
    ["뉴스", "키워드", "유사도·토픽", "검색 추이", "해석·한계"]
)

# ── 뉴스 ───────────────────────────────────────────────────
with tab_news:
    st.markdown('<p class="lead">질문: 브랜드별로 어떤 내용의 기사가 나왔는가?</p>', unsafe_allow_html=True)
    cols = st.columns(len(BRANDS))
    for col, brand in zip(cols, BRANDS):
        col.metric(f"{brand} 기사 수", int((news["브랜드"] == brand).sum()))

    st.subheader("브랜드별 주제 구성")
    st.markdown(
        '<p class="read-hint">막대 하나가 브랜드 하나입니다. 색은 주제, 길이는 기사 수입니다.</p>',
        unsafe_allow_html=True,
    )
    counts = news.groupby(["브랜드", "주제"]).size().reset_index(name="건수")
    chart = (
        alt.Chart(counts)
        .mark_bar(size=34)
        .encode(
            y=alt.Y("브랜드:N", sort=BRANDS, title=None),
            x=alt.X("건수:Q", stack="zero", title="기사 수"),
            color=alt.Color("주제:N", scale=topic_scale(), sort=TOPICS, title="주제"),
            tooltip=["브랜드", "주제", "건수"],
        )
        .properties(height=190)
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("기사 목록")
    st.markdown(
        '<p class="read-hint">브랜드와 주제로 걸러서 원문을 확인할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
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
    st.markdown('<p class="lead">질문: 브랜드와 주제에서 자주 나오거나 특징적인 단어는 무엇인가?</p>', unsafe_allow_html=True)
    st.subheader("워드클라우드")
    st.markdown(
        '<p class="read-hint">윗줄은 BoW(등장 횟수), 아랫줄은 TF-IDF(특징성)입니다. '
        '같은 단어라도 두 줄에서 크기가 다를 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    brand_pick = st.selectbox("브랜드", BRANDS, key="kw_brand")
    img = FIGS / f"wordcloud_{brand_pick}.png"
    if img.exists():
        st.image(str(img), use_container_width=True)
    else:
        st.warning(f"워드클라우드 파일이 없습니다: {img.name}")

    st.subheader("상위 키워드 비교")
    st.markdown(
        '<p class="read-hint">BoW 값은 등장 횟수, TF-IDF 값은 가중치입니다. 단위가 달라서 두 방식의 숫자를 직접 비교하지 않습니다.</p>',
        unsafe_allow_html=True,
    )
    k1, k2 = st.columns(2)
    k_brand = k1.selectbox("브랜드 ", BRANDS, key="kw_brand2")
    k_topic = k2.selectbox("주제", ["전체"] + TOPICS, key="kw_topic")
    sub = keywords[(keywords["브랜드"] == k_brand) & (keywords["주제"] == k_topic)]
    if sub.empty:
        st.info("이 조합에는 기사가 없어서 키워드가 없습니다.")
    else:
        left, right = st.columns(2)
        for col, method in zip((left, right), ["BoW", "TF-IDF"]):
            part = sub[sub["방식"] == method][["순위", "키워드", "값"]]
            col.markdown(f"**{method}**")
            col.dataframe(part, hide_index=True, use_container_width=True)

# ── 유사도·토픽 ────────────────────────────────────────────
with tab_sim:
    st.markdown(
        '<p class="lead">질문: 브랜드와 주제 조합 중 어떤 칸끼리 내용이 비슷한가?</p>',
        unsafe_allow_html=True,
    )
    st.subheader("브랜드·주제 조합 간 유사도")
    st.markdown(
        '<p class="read-hint">진할수록 단어 구성이 비슷합니다(코사인 유사도, 0~1). '
        '기사 수가 적은 칸은 값이 불안정할 수 있습니다.</p>',
        unsafe_allow_html=True,
    )
    idx_name = sim.index.name or "index"
    sim_long = sim.reset_index().melt(id_vars=idx_name, var_name="칸2", value_name="유사도")
    sim_long = sim_long.rename(columns={idx_name: "칸1"})
    heat = (
        alt.Chart(sim_long)
        .mark_rect()
        .encode(
            x=alt.X("칸2:N", sort=list(sim.columns), title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("칸1:N", sort=list(sim.index), title=None),
            color=alt.Color("유사도:Q", scale=alt.Scale(range=["#FFFFFF", "#2F3E4E"], domain=[0, 1]),
                            title="유사도"),
            tooltip=["칸1", "칸2", alt.Tooltip("유사도:Q", format=".3f")],
        )
        .properties(height=440)
    )
    st.altair_chart(heat, use_container_width=True)

    st.subheader("NMF 토픽 (기사 묶음을 단어로 해석)")
    st.markdown(
        '<p class="read-hint">사람이 정한 주제 없이 단어 묶음으로 기사를 나눈 결과입니다. 이름은 단어를 보고 붙였습니다.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(nmf_topics, hide_index=True, use_container_width=True)

    st.subheader("NMF 토픽과 규칙 기반 주제 비교")
    st.markdown(
        '<p class="read-hint">행은 NMF 토픽, 열은 규칙 기반 주제입니다. 한 행에 여러 열이 높으면 분류 기준이 흔들린 것입니다.</p>',
        unsafe_allow_html=True,
    )
    st.dataframe(nmf_cross, use_container_width=True)

# ── 검색 추이 ──────────────────────────────────────────────
with tab_trend:
    st.markdown(
        '<p class="lead">질문: 브랜드별 검색 관심은 언제 높았고, 누가 찾는가?</p>',
        unsafe_allow_html=True,
    )
    st.subheader("월별 검색 추이")
    st.markdown(
        '<p class="read-hint">같은 요청 안에서 가장 높은 달을 100으로 맞춘 상대 지수입니다. '
        '브랜드끼리만 비교하고, 다른 요청의 값과는 비교하지 않습니다.</p>',
        unsafe_allow_html=True,
    )
    line = (
        alt.Chart(monthly)
        .mark_line(point=True)
        .encode(
            x=alt.X("기간:T", title=None, axis=alt.Axis(format="%y.%m")),
            y=alt.Y("지수:Q", title="검색 지수 (최대 100)", scale=alt.Scale(domain=[0, 105])),
            color=alt.Color("브랜드:N", scale=brand_scale(), title="브랜드"),
            tooltip=["브랜드", alt.Tooltip("기간:T", format="%Y.%m"), alt.Tooltip("지수:Q", format=".1f")],
        )
        .properties(height=320)
    )
    st.altair_chart(line, use_container_width=True)

    st.subheader("연령별 구성")
    st.markdown(
        '<p class="read-hint">각 브랜드 안에서 연령별 비중을 합 100%로 맞춘 값입니다. 브랜드끼리 크기를 비교하지 않고 모양만 봅니다.</p>',
        unsafe_allow_html=True,
    )
    age = segment[segment["구분종류"] == "연령"]
    age_chart = (
        alt.Chart(age)
        .mark_bar()
        .encode(
            y=alt.Y("구분:N", sort=None, title=None),
            x=alt.X("상대비중:Q", axis=alt.Axis(format=".0%"), title="상대 비중"),
            color=alt.Color("브랜드:N", scale=brand_scale(), title="브랜드"),
            yOffset="브랜드:N",
            tooltip=["브랜드", "구분", alt.Tooltip("상대비중:Q", format=".1%")],
        )
        .properties(height=380)
    )
    st.altair_chart(age_chart, use_container_width=True)

    st.subheader("성별·기기 구성")
    gd = segment[segment["구분종류"].isin(["성별", "기기"])]
    gd_chart = (
        alt.Chart(gd)
        .mark_bar(size=34)
        .encode(
            y=alt.Y("브랜드:N", sort=BRANDS, title=None),
            x=alt.X("상대비중:Q", stack="normalize", axis=alt.Axis(format=".0%"), title=None),
            color=alt.Color("구분:N", title=None),
            row=alt.Row("구분종류:N", title=None, header=alt.Header(labelAngle=0, labelFontSize=13)),
            tooltip=["브랜드", "구분종류", "구분", alt.Tooltip("상대비중:Q", format=".1%")],
        )
        .properties(height=110, width=620)
    )
    st.altair_chart(gd_chart)

# ── 해석·한계 ──────────────────────────────────────────────
with tab_notes:
    st.markdown('<p class="lead">질문: 이 결과는 어디까지 믿을 수 있는가?</p>', unsafe_allow_html=True)
    st.markdown(
        """
**뉴스에서 본 것**
- 유니클로: 실적·사업과 협업 기사가 많고, 양말 가격 인상 이슈가 크게 다뤄졌습니다.
- 스파오: 제품 출시(경량패딩, 발열내의)가 많고, 이랜드 소장품 기사가 섞여 있습니다.
- 탑텐: '텐텐데이' 할인 기사가 대부분입니다. 같은 보도자료가 여러 언론에 실려 중복이 많습니다.

**검색 추이에서 본 것**
- 유니클로 검색량이 가장 큽니다. 2025년 10~12월과 2026년 5월에 높았습니다.
- 탑텐은 2025년 10월에 뚜렷하게 솟았습니다. 행사 시기와 겹치는 것으로 보이지만 가설입니다.
- 스파오는 2026년 들어 점진적으로 오르고 있습니다.

**한계**
- 뉴스는 검색 API가 준 요약 기준이라 본문 전체를 본 것이 아닙니다.
- 관련성 판정과 주제 분류는 키워드 규칙 기반이라 오분류가 있습니다.
- 검색 지수는 요청마다 상대 지수라서 같은 요청 안에서만 비교가 유효합니다.
- 연령·성별·기기 비중은 요청을 나눠 받은 근사치입니다.
"""
    )

st.markdown(
    '<p class="source">데이터: 네이버 뉴스 검색 API (수집 2026-10-31, 브랜드별 50건, 정제 후 150건) · '
    'DataLab 검색 추이 API (2025.01~2026.09, 월 단위). 검색 지수는 요청별 상대 지수입니다.</p>',
    unsafe_allow_html=True,
)
