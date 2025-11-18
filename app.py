import streamlit as st
import pandas as pd
from analysis import analyze_company   # 당신이 만든 analysis.py 사용

st.set_page_config(page_title="기업 재무 분석", layout="wide")

# ------------------------------------------------------
# 0. 간단한 "라우터" : search / dashboard 두 화면만 사용
# ------------------------------------------------------
if "view" not in st.session_state:
    st.session_state["view"] = "search"   # 처음에는 검색 화면
if "search_q" not in st.session_state:
    st.session_state["search_q"] = ""


def go_search():
    st.session_state["view"] = "search"
    # st.rerun() / st.experimental_rerun() 필요 없음


def go_dashboard(q: str):
    st.session_state["search_q"] = q
    st.session_state["view"] = "dashboard"
    # st.rerun() / st.experimental_rerun() 필요 없음

# ------------------------------------------------------
# 1. 검색 화면
# ------------------------------------------------------
def render_search_page():
    st.title("기업 재무 분석")

    q = st.text_input(
        "회사명 또는 종목코드 (예: 삼성전자 또는 005930)",
        value=st.session_state.get("search_q", ""),
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("분석", type="primary"):
            q_strip = q.strip()
            if not q_strip:
                st.warning("회사명 또는 종목코드를 입력해 주세요.")
            else:
                go_dashboard(q_strip)

    with col2:
        st.caption("DART + pykrx + 네이버 증권 데이터를 활용해 기본적인 밸류에이션과 펀더멘털을 보여줍니다.")


# ------------------------------------------------------
# 2. 대시보드 화면
# ------------------------------------------------------
def render_dashboard_page():
    q = st.session_state.get("search_q", "").strip()
    if not q:
        # 검색어가 없으면 검색 화면으로 복귀
        go_search()
        return

    # 상단 영역
    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("← 검색으로"):
            go_search()

    with col_title:
        st.title(f"'{q}' 분석 대시보드")

    # 데이터 분석
    with st.spinner("데이터 분석 중..."):
        data = analyze_company(q)

    # --- KPI 카드 ---
    c1, c2, c3, c4 = st.columns(4)

    price = data.get("price")
    fair = data.get("fair_value")
    disc = data.get("undervaluation_pct")
    score = data.get("score_total")

    def fmt_number(v):
        return f"{v:,.0f}" if isinstance(v, (int, float)) else "N/A"

    def fmt_pct(v):
        return f"{v:+.1f}%" if isinstance(v, (int, float)) else "N/A"

    c1.metric("현재가", fmt_number(price) + " 원")
    c2.metric("적정가(추정)", fmt_number(fair) + " 원")
    c3.metric("저/고평가율", fmt_pct(disc))
    c4.metric("펀더멘털 총점", f"{score:.1f}" if isinstance(score, (int, float)) else "N/A")

    st.caption(f"분석 기준일: {data.get('basis_date', 'N/A')}")

    # --- 탭 구성 ---
    tab1, tab2, tab3 = st.tabs(["차트", "펀더멘털 지표", "업종 비교"])

    # 2-1. 차트 탭
    with tab1:
        st.subheader("가격 및 적정가 추이")
        hist = data.get("history")
        if isinstance(hist, pd.DataFrame) and not hist.empty:
            show_cols = [c for c in ["date", "price", "fair_value_est"] if c in hist.columns]
            st.dataframe(hist[show_cols].tail(200), use_container_width=True)

            chart_cols = ["price"]
            if "fair_value_est" in hist.columns:
                chart_cols.append("fair_value_est")
            chart_df = hist.set_index("date")[chart_cols]
            st.line_chart(chart_df)
        else:
            st.info("가격 히스토리 데이터가 없습니다.")

    # 2-2. 펀더멘털 탭
    with tab2:
        st.subheader("핵심 펀더멘털 지표")
        stats = pd.DataFrame(
            {
                "지표": ["ROE(%)", "영업이익률(%)", "부채비율(%)", "매출성장률(%)", "PER", "PBR", "EPS", "BPS"],
                "값": [
                    data.get("roe"),
                    data.get("op_margin"),
                    data.get("debt_ratio"),
                    data.get("sales_growth"),
                    data.get("PER"),
                    data.get("PBR"),
                    data.get("EPS"),
                    data.get("BPS"),
                ],
            }
        )
        st.dataframe(stats, use_container_width=True)

    # 2-3. 업종 비교 탭
    with tab3:
        st.subheader("업종 평균 PER 비교")
        peer = data.get("peer_summary") or {}
        if peer.get("peer_count_used", 0) > 0:
            st.write(f"업종명: {peer.get('sector_name', 'N/A')}")
            st.write(
                f"종목 PER: {peer.get('target_value', float('nan')):.2f}배, "
                f"업종 평균 PER: {peer.get('sector_avg', float('nan')):.2f}배"
            )
            if peer.get("discount_pct") is not None:
                st.write(
                    f"상대 PER: {peer.get('relative', float('nan')):.2f}배, "
                    f"할인율: {peer.get('discount_pct', float('nan')):+.1f}%"
                )
        else:
            st.info("업종 비교 데이터가 없습니다.")


# ------------------------------------------------------
# 3. 메인 분기
# ------------------------------------------------------
if st.session_state["view"] == "search":
    render_search_page()
else:
    render_dashboard_page()
