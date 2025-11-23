# app_with_ngrok.py
import streamlit as st
from diary_storage import DiaryStorage
from diary_pdf import DiaryPDFMaker
from datetime import datetime, timedelta
import os
from pyngrok import ngrok
import threading
import atexit

# =============================
# 전역 ngrok 터널 관리
# =============================
_ngrok_tunnel = None
_ngrok_initialized = False

def start_ngrok():
    """ngrok 터널 시작 및 공개 URL 생성 (최초 1회만)"""
    global _ngrok_tunnel, _ngrok_initialized
    
    # 이미 초기화되었으면 기존 터널 반환
    if _ngrok_initialized and _ngrok_tunnel:
        return _ngrok_tunnel
    
    try:
        # 기존 터널 확인
        tunnels = ngrok.get_tunnels()
        if tunnels:
            # 기존 터널이 있으면 재사용
            _ngrok_tunnel = tunnels[0].public_url
            _ngrok_initialized = True
            print(f"\n✅ 기존 ngrok 터널 재사용: {_ngrok_tunnel}\n")
            return _ngrok_tunnel
        
        # ngrok authtoken 설정 (환경변수에서 가져오기)
        ngrok_token = os.getenv('NGROK_AUTHTOKEN')
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
        
        # Streamlit의 기본 포트는 8501
        port = 8501
        
        # ngrok 터널 생성
        _ngrok_tunnel = ngrok.connect(port, bind_tls=True)
        _ngrok_initialized = True
        
        # 터미널에만 출력 (최초 1회)
        print("\n" + "="*60)
        print("🌐 Ngrok 터널 생성 완료!")
        print("="*60)
        print(f"📡 공개 URL: {_ngrok_tunnel}")
        print(f"🔗 외부에서 이 URL로 접속하세요!")
        print("="*60 + "\n")
        
        return _ngrok_tunnel
        
    except Exception as e:
        print(f"\n⚠️ Ngrok 시작 실패: {e}")
        print("💡 Ngrok authtoken을 설정하지 않았다면, 무료 계정을 만들고 토큰을 설정하세요:")
        print("   1. https://ngrok.com 에서 가입")
        print("   2. authtoken 받기")
        print("   3. 환경변수 설정: export NGROK_AUTHTOKEN='your_token_here'\n")
        _ngrok_initialized = True  # 실패해도 재시도 방지
        return None

def cleanup_ngrok():
    """앱 종료 시 ngrok 터널 정리"""
    global _ngrok_tunnel
    if _ngrok_tunnel:
        try:
            ngrok.disconnect(_ngrok_tunnel)
            print("\n🔌 Ngrok 터널 종료됨\n")
        except:
            pass

# 앱 종료 시 정리 함수 등록
atexit.register(cleanup_ngrok)

# ngrok 터널 시작 (전역 변수로 관리, 최초 1회만 실행)
if not _ngrok_initialized:
    ngrok_url = start_ngrok()
    # 세션 상태에도 저장 (참고용)
    if 'ngrok_url' not in st.session_state:
        st.session_state.ngrok_url = ngrok_url

st.set_page_config(
    page_title="MyGreen",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================
# 저장소 초기화
# =============================
@st.cache_resource
def get_storage():
    return DiaryStorage()

storage = get_storage()

# =============================
# 더미 데이터 - 식물 정보
# =============================
DUMMY_PLANTS = [
    {
        "nickname": "메밀이",
        "species": "메밀",
        "planted_date": datetime(2025, 10, 28),  # 심은 날짜
    },
    {
        "nickname": "과꽃2호기",
        "species": "과꽃",
        "planted_date": datetime(2025, 10, 29),
    },
    {
        "nickname": "로즈",
        "species": "장미",
        "planted_date": datetime(2025, 10, 10),
    },
]

def calculate_days_since(planted_date):
    """심은지 며칠째인지 계산"""
    delta = datetime.now() - planted_date
    return delta.days

def get_plant_info(nickname):
    """닉네임으로 식물 정보 가져오기"""
    for plant in DUMMY_PLANTS:
        if plant["nickname"] == nickname:
            return plant
    return None

# =============================
# 세션 상태
# =============================
if "tab" not in st.session_state:
    st.session_state.tab = "홈"

if "show_pdf_modal" not in st.session_state:
    st.session_state.show_pdf_modal = False

if "pdf_plant_name" not in st.session_state:
    st.session_state.pdf_plant_name = None

if "pdf_generated" not in st.session_state:
    st.session_state.pdf_generated = False

def goto(tab): 
    st.session_state.tab = tab

# =============================
# CSS 스타일
# =============================
st.markdown("""
<style>
/* 기본 레이아웃 설정 */
html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow-x: hidden;
}

/* Streamlit 기본 요소 숨기기 */
footer {display: none !important;}
.stApp {
    overflow-x: hidden;
    position: relative;
    min-height: 100vh;
}

/* 사이드바 완전 숨김 */
section[data-testid="stSidebar"] {display: none !important;}
div[data-testid="collapsedControl"] {display: none !important;}
header {visibility: hidden; height: 0 !important;}

/* 전체 컨테이너: 웹페이지 사이즈(최대 1280px), 중앙정렬 */
.block-container {
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding-top: 1rem !important;
    padding-bottom: 80px !important;
}

/* 로고 */
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

/* 카드 */
.card {
    border: 1px solid #e6e6e6;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    position: relative;
}

/* 카드 헤더 */
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}

.card-title-area {
    flex: 1;
}

.card-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}

/* PDF 버튼 (우측 상단) */
.pdf-button-container {
    margin-left: 12px;
}

/* 카드 정보 */
.card-info-row {
    display: flex;
    justify-content: space-between;
    color: #7c7c7c;
    font-size: 13px;
    margin-top: 4px;
}

/* 두 개의 버튼 (기록 작성, 대화 하기) */
.action-row {
    display: flex;
    gap: 10px;
    margin-top: 16px;
}
.action-btn {
    flex: 1;
    padding: 12px;
    border-radius: 12px;
    border: none;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    color: white !important;
    background: #2f6f3e;
    text-decoration: none !important;
    text-align: center;
    display: block;
    transition: all 0.2s;
}
.action-btn:hover {
    background: #265a32;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(47, 111, 62, 0.3);
}
.action-btn.secondary {
    background: #4e8b5c;
}
.action-btn.secondary:hover {
    background: #3d6e48;
}

/* 하단 네비게이션 - 화면 하단 고정 */
#bottom-nav {
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    height: 65px !important;
    background-color: #ffffff !important;
    border-top: 1px solid #e0e0e0 !important;
    z-index: 99999 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 -1px 3px rgba(0,0,0,0.05) !important;
}

#bottom-nav .nav-content {
    max-width: 1280px;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-around;
    padding: 0 20px;
}

#bottom-nav .nav-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    cursor: pointer;
    color: #333333;
    font-size: 13px;
    padding: 8px 4px;
    transition: all 0.2s;
    text-decoration: none;
}

#bottom-nav .nav-item:hover {
    background: #f8f8f8;
    color: #2f6f3e;
}

#bottom-nav .nav-icon {
    font-size: 20px;
    margin-bottom: 2px;
}

#bottom-nav .nav-text {
    font-size: 12px;
    font-weight: 400;
}

/* 모달 스타일 */
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
}

.modal-content {
    background: white;
    padding: 30px;
    border-radius: 16px;
    max-width: 400px;
    width: 90%;
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.modal-title {
    font-size: 18px;
    font-weight: 700;
    color: #2f6f3e;
    margin-bottom: 15px;
    text-align: center;
}

.modal-text {
    font-size: 14px;
    color: #666;
    margin-bottom: 20px;
    text-align: center;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

# =============================
# 로고 바
# =============================
st.markdown("""
<div class="logo-bar">
    <a href="/" target='_self' class="logo-btn">MyGreen</a>
</div>
""", unsafe_allow_html=True)

# =============================
# PDF 생성 함수
# =============================
def generate_pdf(plant_name):
    """PDF 생성"""
    try:
        # 일지 데이터 확인
        diaries = storage.get_plant_diaries(plant_name)
        
        if len(diaries) == 0:
            return None, "일지가 없습니다."
        
        # 통계 가져오기
        stats = storage.get_statistics(plant_name)
        
        # PDF 생성
        pdf_maker = DiaryPDFMaker()
        pdf_path = pdf_maker.create_diary_book(diaries, plant_name, stats)
        
        return pdf_path, None
    
    except Exception as e:
        return None, f"PDF 생성 중 오류: {str(e)}"

# =============================
# 식물 카드 렌더링
# =============================
def plant_card(plant_info):
    """식물 카드 렌더링"""
    nickname = plant_info["nickname"]
    species = plant_info["species"]
    planted_date = plant_info["planted_date"]
    
    # 계산
    days_since = calculate_days_since(planted_date)
    planted_str = planted_date.strftime('%Y.%m.%d')
    
    # 저장된 일지 수 확인
    diaries = storage.get_plant_diaries(nickname)
    diary_count = len(diaries)
    
    # 마지막 기록 날짜
    if diary_count > 0:
        last_diary_date = diaries.iloc[-1]['날짜']
        last_str = last_diary_date.strftime('%y.%m.%d %H:%M')
    else:
        last_str = "기록 없음"
    
    # 카드 HTML
    st.markdown(f"""
    <div class="card">
        <div class="card-header">
            <div class="card-title-area">
                <div class="card-title">
                    <div style="font-weight:800;font-size:17px">{nickname}</div>
                    <div style="color:#7c7c7c;margin-left:6px">{species}</div>
                </div>
                <div class="card-info-row">
                    <div>만난 날짜</div><div>{planted_str} ({days_since}일째)</div>
                </div>
                <div class="card-info-row">
                    <div>마지막 기록</div><div>{last_str}</div>
                </div>
                <div class="card-info-row">
                    <div>총 일지 수</div><div>{diary_count}개</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 버튼 영역
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col2:
        # 기록 작성 버튼 - 식물 이름을 쿼리 파라미터로 전달
        if st.button("📝 일지 작성", key=f"write_{nickname}", use_container_width=True):
            # 세션 스테이트에 선택된 식물 저장
            st.session_state["selected_plant"] = nickname
            st.switch_page("pages/mindcoach.py")
    
    with col1:
        # 대화 하기 버튼 - 식물 이름을 세션에 저장하고 communication 페이지로 이동
        if st.button("💬 대화 하기", key=f"chat_{nickname}", use_container_width=True):
            st.session_state["selected_plant"] = nickname
            st.switch_page("pages/voice_chat.py")
    
    with col3:
        # PDF 생성 버튼 (우측)
        if st.button("📖 일지 출간", key=f"pdf_{nickname}", use_container_width=True, help="일지 출간"):
            st.session_state.pdf_plant_name = nickname
            st.session_state.show_pdf_modal = True
            st.rerun()

# =============================
# 모달 처리
# =============================
if st.session_state.show_pdf_modal and st.session_state.pdf_plant_name:
    plant_name = st.session_state.pdf_plant_name
    diaries = storage.get_plant_diaries(plant_name)
    
    if len(diaries) == 0:
        # 일지가 없는 경우
        st.markdown(f"""
        <div class="modal-backdrop" onclick="window.location.reload()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-title">📭 일지가 없습니다</div>
                <div class="modal-text">
                    <b>{plant_name}</b>의 일지가 아직 없습니다.<br>
                    먼저 일지를 작성해주세요!
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3초 후 자동 닫기
        import time
        time.sleep(2)
        st.session_state.show_pdf_modal = False
        st.session_state.pdf_plant_name = None
        st.rerun()
    
    else:
        # 일지가 있는 경우 - PDF 생성
        if not st.session_state.pdf_generated:
            with st.spinner(f"📖 {plant_name}의 일지를 책자로 만드는 중..."):
                pdf_path, error = generate_pdf(plant_name)
                
                if error:
                    st.error(f"❌ {error}")
                    st.session_state.show_pdf_modal = False
                    st.session_state.pdf_plant_name = None
                else:
                    st.session_state.pdf_generated = True
                    st.session_state.pdf_path = pdf_path
                    st.rerun()
        
        else:
            # PDF 다운로드 제공
            pdf_path = st.session_state.pdf_path
            
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    pdf_data = pdf_file.read()
                
                st.success("✅ PDF 생성 완료!")
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.download_button(
                        label=f"📥 {plant_name}_일지.pdf 다운로드",
                        data=pdf_data,
                        file_name=f"{plant_name}_일지.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                
                with col2:
                    if st.button("닫기", use_container_width=True):
                        st.session_state.show_pdf_modal = False
                        st.session_state.pdf_plant_name = None
                        st.session_state.pdf_generated = False
                        st.rerun()
                
                # 통계 미리보기
                stats = storage.get_statistics(plant_name)
                st.markdown("---")
                st.markdown(f"**📊 {plant_name}의 통계**")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("총 일지 수", f"{stats['총_일지_수']}개")
                with col_b:
                    st.metric("평균 감정 점수", f"{stats['평균_감정점수']}점")
                with col_c:
                    st.metric("최근 7일 평균", f"{stats['최근_7일_평균']}점")

# =============================
# 각 페이지
# =============================
def page_home():
    st.subheader("내 식물 🌱")
    
    # 더미 데이터의 모든 식물 표시
    for plant_info in DUMMY_PLANTS:
        plant_card(plant_info)

def page_mypage():
    st.subheader("마이페이지")
    st.write("프로필, 설정 등")

# =============================
# 라우팅
# =============================
if st.session_state.tab == "홈": 
    page_home()
elif st.session_state.tab == "마이페이지": 
    page_mypage()

# =============================
# 하단 네비게이션 (HTML로 직접 구현)
# =============================
st.markdown("""
<div id="bottom-nav">
    <div class="nav-content">
        <a href="/" target="_self" class="nav-item" id="nav-home">
            <div class="nav-icon">🏠</div>
            <div class="nav-text">홈</div>
        </a>
        <a href="/plantdoc" target="_self" class="nav-item" id="nav-hospital">
            <div class="nav-icon">🌿</div>
            <div class="nav-text">식물 병원</div>
        </a>
        <a href="https://mygreen.co.kr/?menu=my_page" target="_blank" class="nav-item" id="nav-mypage">
            <div class="nav-icon">👤</div>
            <div class="nav-text">마이페이지</div>
        </a>
    </div>
</div>
""", unsafe_allow_html=True)