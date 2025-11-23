# pages/plantdoc.py
import streamlit as st

# =============================
# 세션 상태 초기화 (app_doc.py보다 먼저 실행)
# =============================
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.show_crop_selection = True

if "current_crop" not in st.session_state:
    st.session_state.current_crop = None

if "crop_loading" not in st.session_state:
    st.session_state.crop_loading = {}

if "crop_data" not in st.session_state:
    st.session_state.crop_data = {}

if "waiting_for_diagnosis" not in st.session_state:
    st.session_state.waiting_for_diagnosis = False

if "similar_diseases" not in st.session_state:
    st.session_state.similar_diseases = []

if "show_crop_selection" not in st.session_state:
    st.session_state.show_crop_selection = True

if "pending_symptom" not in st.session_state:
    st.session_state.pending_symptom = None

# =============================
# app_doc 임포트 (세션 상태 초기화 후)
# =============================
from app_doc import main as hospital_main

# =============================
# 상단 로고 영역
# =============================
st.markdown("""
<style>
/* 사이드바 완전 숨김 */
section[data-testid="stSidebar"] {display: none !important;}
div[data-testid="collapsedControl"] {display: none !important;}
header {visibility: hidden; height: 0 !important;}

/* 페이지 컨테이너 */
.block-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding-top: 1rem !important;
}

/* 상단 로고 바 */
.logo-bar {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding: 12px 8px;
    background-color: #ffffff;
    border-bottom: 1px solid #eee;
    position: sticky;
    top: 0;
    z-index: 1000;
}

/* MyGreen 로고 스타일 */
.logo-btn {
    font-size: 28px;
    font-weight: 900;
    color: #2f6f3e !important;
    background: none;
    border: none;
    text-decoration: none !important;
    cursor: pointer;
    letter-spacing: .5px;
}

/* hover 효과 */
.logo-btn:hover {
    color: #1f4d2c !important;
    text-decoration: none !important;
}
</style>

<!-- 상단 로고: 클릭 시 메인(app.py)으로 이동 -->
<div class="logo-bar">
    <a href="/" target='_self' class="logo-btn">MyGreen</a>
</div>
""", unsafe_allow_html=True)

# =============================
# 기존 식물 병원(챗봇) 메인 실행
# =============================
hospital_main()