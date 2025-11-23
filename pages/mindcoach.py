# pages/mindcoach.py
import os
import streamlit as st
from mind_coach import MindCoachRAG
from diary_storage import DiaryStorage

# 페이지 기본 설정
st.set_page_config(
    page_title="Mind Coach",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
# API 키 확인
# =============================
def check_api_key():
    """OpenAI API 키 확인"""
    if "OPENAI_API_KEY" not in os.environ:
        st.error("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        st.info("""
        **설정 방법:**
        1. `.env` 파일 생성
        2. `OPENAI_API_KEY=your-api-key` 추가
        """)
        st.stop()


# =============================
# Mind Coach 및 Storage 초기화
# =============================
@st.cache_resource
def initialize_mind_coach():
    """Mind Coach 시스템 초기화 (캐싱)"""
    api_key = os.environ.get("OPENAI_API_KEY")
    mind_coach = MindCoachRAG(openai_api_key=api_key)
    
    # Vector DB 초기화
    success_high, success_low = mind_coach.initialize_vector_dbs()
    
    return mind_coach, success_high, success_low

@st.cache_resource
def initialize_storage():
    """일지 저장소 초기화 (캐싱)"""
    return DiaryStorage()


# =============================
# Mind Coach 메인 함수
# =============================
def mind_coach_main():
    """Mind Coach 메인 함수"""
    
    # API 키 확인
    check_api_key()
    
    # Mind Coach 초기화
    mind_coach, success_high, success_low = initialize_mind_coach()
    
    # 저장소 초기화
    storage = initialize_storage()
    
    if not success_high and not success_low:
        st.warning("⚠️ PDF 파일을 찾을 수 없어 기본 메시지로 동작합니다.")
    
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    
    # 메인 화면에서 선택된 식물이 있는지 확인
    if "selected_plant" in st.session_state and st.session_state["selected_plant"]:
        # 메인에서 선택된 식물이 있으면 자동으로 설정
        if "current_plant" not in st.session_state or st.session_state["current_plant"] is None:
            st.session_state["current_plant"] = st.session_state["selected_plant"]
            st.session_state["messages"] = []  # 새 식물 선택 시 메시지 초기화
    
    if "current_plant" not in st.session_state:
        st.session_state["current_plant"] = None
    
    # 식물 선택 (처음에만 또는 current_plant가 없을 때)
    if st.session_state["current_plant"] is None:
        st.markdown("""
        <div style="text-align:center; padding:40px 20px; color:#7c7c7c;">
            <div style="font-size:48px; margin-bottom:16px;">🌱</div>
            <div style="font-size:18px; font-weight:600; margin-bottom:8px;">
                어떤 식물과 함께 하실건가요?
            </div>
            <div style="font-size:14px;">
                식물 이름(별명)을 입력해주세요
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 기존 식물 목록 표시
        existing_plants = storage.get_all_plants()
        if existing_plants:
            st.markdown("### 기존 식물 선택")
            cols = st.columns(min(len(existing_plants), 3))
            for idx, plant in enumerate(existing_plants):
                with cols[idx % 3]:
                    if st.button(f"🌿 {plant}", key=f"plant_{plant}", use_container_width=True):
                        st.session_state["current_plant"] = plant
                        st.session_state["messages"] = []
                        st.rerun()
            
            st.markdown("---")
        
        # 새 식물 입력
        st.markdown("### 새 식물 시작")
        new_plant = st.text_input("식물 이름 입력", placeholder="예: 메밀이, 과꽃2호기, 로즈...")
        if st.button("시작하기", type="primary", use_container_width=True):
            if new_plant.strip():
                st.session_state["current_plant"] = new_plant.strip()
                st.session_state["messages"] = []
                st.rerun()
            else:
                st.error("식물 이름을 입력해주세요!")
        
        return
    
    # 현재 식물 표시
    plant_name = st.session_state["current_plant"]
    
    # 상단에 현재 식물 표시 + 변경 버튼
    st.markdown(f"""
        <div style="padding:16px; background:#f0f7f4; border-radius:12px; margin-bottom:20px;">
            <div style="font-size:20px; font-weight:700; color:#2f6f3e;">
                🌱 {plant_name}
            </div>
            <div style="font-size:13px; color:#666; margin-top:4px;">
                함께 성장하는 마음 일지
            </div>
        </div>
        """, unsafe_allow_html=True)

    
    # 대화 기록 표시
    if len(st.session_state["messages"]) == 0:
        st.markdown("""
        <div style="text-align:center; padding:40px 20px; color:#7c7c7c;">
            <div style="font-size:18px; font-weight:600; margin-bottom:8px;">
                오늘 하루는 어떠셨나요?
            </div>
            <div style="font-size:14px;">
                자유롭게 이야기해주세요
            </div>
        </finalist>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state["messages"]:
            if message["role"] == "user":
                st.markdown(f"""
                <div style="
                    background: #f0f7f4;
                    border-left: 4px solid #2f6f3e;
                    border-radius: 16px;
                    padding: 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                ">
                    <div style="font-size:13px; color:#2f6f3e; font-weight:600; margin-bottom:8px;">나</div>
                    <div>{message["content"]}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="
                    background: #ffffff;
                    border: 1px solid #e6e6e6;
                    border-radius: 16px;
                    padding: 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                ">
                    <div style="font-size:13px; color:#2f6f3e; font-weight:600; margin-bottom:12px;">
                        🌱 Mind Coach
                    </div>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
    
    # 채팅 입력
    user_input = st.chat_input("오늘 하루는 어떠셨나요? 자유롭게 이야기해주세요 🌱")
    
    if user_input:
        # 사용자 메시지 저장
        st.session_state["messages"].append({
            "role": "user",
            "content": user_input
        })
        
        # AI 응답 생성
        with st.spinner("마음을 분석하는 중..."):
            try:
                result = mind_coach.get_full_response(user_input)
                
                # 일지 저장
                save_success = storage.save_diary(
                    plant_name=plant_name,
                    diary_content=user_input,
                    analysis_result=result
                )
                
                if not save_success:
                    st.warning("⚠️ 일지 저장에 실패했습니다.")
                
                # 응답 포맷팅
                if result['emotion'] >= 70:
                    badge_bg = "#e8f5e9"
                    badge_color = "#2e7d32"
                elif result['emotion'] >= 40:
                    badge_bg = "#fff8e1"
                    badge_color = "#f57f17"
                else:
                    badge_bg = "#ffebee"
                    badge_color = "#c62828"
                
                plant_advice_formatted = result["plant_advice"].replace(". ", ".<br>")
                
                formatted_response = f"""
                <div style="font-size:16px; font-weight:700; color:#2f6f3e; margin:16px 0 8px 0;">📊 감정 분석</div>
                <div style="
                    display: inline-block;
                    padding: 6px 14px;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: 600;
                    margin: 8px 0;
                    background: {badge_bg};
                    color: {badge_color};
                ">
                    {result['emotion_color']} {result['emotion_label']} ({result['emotion']}점)
                </div>
                
                <div style="font-size:16px; font-weight:700; color:#2f6f3e; margin:16px 0 8px 0;">💭 오늘의 요약</div>
                <div style="padding:8px 0; color:#333;">{result["summary"]}</div>
                
                <div style="font-size:16px; font-weight:700; color:#2f6f3e; margin:16px 0 8px 0;">💚 응원의 메시지</div>
                <div style="padding:8px 0; color:#333;">{result["cheer"]}</div>
                
                <div style="font-size:16px; font-weight:700; color:#2f6f3e; margin:16px 0 8px 0;">🌱 오늘의 MYGREEN</div>
                <div style="padding:8px 0; color:#555; font-style:italic; line-height:1.8;">
                    {plant_advice_formatted}
                </div>
                <div style="font-size:12px; color:#999; margin-top:8px;">
                    * {result['db_label']} | ✅ 일지 저장 완료
                </div>
                """
                
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": formatted_response
                })
                
            except Exception as e:
                st.error(f"❌ 응답 생성 중 오류가 발생했습니다: {str(e)}")
        
        st.rerun()
    
    # 대화 기록이 있을 때 하단에 버튼 표시
    if len(st.session_state["messages"]) > 0:
        st.markdown("---")
        st.markdown("""
        <style>
        .home-button {
            display: block;
            padding: 0.5rem 1rem;
            background-color: #2f6f3e;
            color: white !important;
            text-align: center;
            text-decoration: none !important;
            border-radius: 0.5rem;
            font-weight: 600;
            transition: all 0.2s;
        }
        .home-button:hover {
            background-color: #265a32;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(47, 111, 62, 0.3);
        }
        </style>
        """, unsafe_allow_html=True)
        
            # 링크 방식으로 홈 이동
        st.markdown("""
            <a href="/" target="_self" class="home-button">
                🏠 홈으로 돌아가기
            </a>
            """, unsafe_allow_html=True)


# =============================
# 메인 실행
# =============================
mind_coach_main()