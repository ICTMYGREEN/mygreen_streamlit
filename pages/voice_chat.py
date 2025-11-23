# pages/voice_chat.py (with plant-specific conversation management)
import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from openai import OpenAI
import base64
from io import BytesIO
try:
    from audio_recorder_streamlit import audio_recorder
    AUDIO_RECORDER_AVAILABLE = True
except ImportError:
    AUDIO_RECORDER_AVAILABLE = False
    st.warning("⚠️ audio_recorder_streamlit 패키지가 설치되지 않았습니다. 음성 입력 기능이 비활성화됩니다.")

# 페이지 기본 설정
st.set_page_config(
    page_title="식물 친구와 채팅",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================
# 카카오톡 스타일 CSS + 상단 로고 영역
# =============================
st.markdown(
    """
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
    padding-bottom: 120px !important;
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

/* 채팅 메시지 컨테이너 */
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 10px 0;
}

/* AI 메시지 (왼쪽) */
.message-left {
    display: flex;
    justify-content: flex-start;
    align-items: flex-start;
    gap: 10px;
    margin-right: 25%;
}

.message-left .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: #e6ffe6;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
}

.message-left .bubble {
    background-color: #e6ffe6;
    padding: 10px 15px;
    border-radius: 15px;
    border-top-left-radius: 3px;
    max-width: 100%;
    word-wrap: break-word;
}

/* User 메시지 (오른쪽) */
.message-right {
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    gap: 10px;
    margin-left: 25%;
}

.message-right .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background-color: #F0F0F0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    order: 2;
}

.message-right .bubble {
    background-color: #F0F0F0;
    padding: 10px 15px;
    border-radius: 15px;
    border-top-right-radius: 3px;
    max-width: 100%;
    word-wrap: break-word;
    order: 1;
}

.bubble {
    font-size: 15px;
    line-height: 1.4;
}

/* 하단 입력 영역 고정 */
.stChatInputContainer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: white;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
    z-index: 999;
}
</style>

<!-- 상단 로고: 클릭 시 메인(app.py)으로 이동 -->
<div class="logo-bar">
    <a href="/" target='_self' class="logo-btn">MyGreen</a>
</div>
""",
    unsafe_allow_html=True,
)

# =============================
# API 키 확인
# =============================
def check_api_key():
    """OpenAI API 키 확인"""
    if "OPENAI_API_KEY" not in os.environ:
        st.error("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        st.info(
            """
        **설정 방법:**
        1. `.env` 파일 생성
        2. `OPENAI_API_KEY=your-api-key` 추가
        """
        )
        st.stop()


# =============================
# LLM 및 OpenAI 클라이언트 초기화 (캐싱)
# =============================
@st.cache_resource
def initialize_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.8,
        frequency_penalty=1.0,
    )

@st.cache_resource
def initialize_openai_client():
    return OpenAI()


# =============================
# TTS/STT 함수
# =============================
def text_to_speech(text):
    """OpenAI TTS API를 사용하여 텍스트를 음성으로 변환"""
    try:
        client = initialize_openai_client()
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # alloy, echo, fable, onyx, nova, shimmer 중 선택 가능
            input=text
        )
        return response.content
    except Exception as e:
        st.error(f"음성 변환 오류: {e}")
        return None

def speech_to_text(audio_file):
    """OpenAI Whisper API를 사용하여 음성을 텍스트로 변환"""
    try:
        client = initialize_openai_client()
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ko"
        )
        return transcript.text
    except Exception as e:
        st.error(f"음성 인식 오류: {e}")
        return None

def create_audio_player(audio_data):
    """base64로 인코딩된 오디오 플레이어 생성"""
    b64 = base64.b64encode(audio_data).decode()
    audio_html = f"""
        <audio  autoplay style="width: 25%; height: 30px;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
    """
    return audio_html


# =============================
# RunnableWithMessageHistory 설정
# =============================

# 세션별 대화 이력 저장소 (Streamlit 세션 내에서 유지)
if "_comm_histories" not in st.session_state:
    st.session_state._comm_histories = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    store = st.session_state._comm_histories
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


def build_chain(persona: int, plantname: str, llm: ChatOpenAI) -> RunnableWithMessageHistory:
    prompt = get_prompt_template(persona, plantname)
    base_chain = prompt | llm | StrOutputParser()

    # RunnableWithMessageHistory가 history를 자동으로 주입/저장
    chain_with_history = RunnableWithMessageHistory(
        base_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    return chain_with_history


# =============================
# 프롬프트 템플릿
# =============================
def get_prompt_template(persona, plantname):
    prompts = {
        0: ChatPromptTemplate.from_template(
            f"""
        너는 친근한 대화를 하는 친구같은 {plantname}야.
        사용자는 일반적인 경우보다 우울감이 심해.
        친구와 채팅 대화하는 것처럼 반말로 1~3문장으로 대화해.
        
        말투: 부드러운 말투

        이전 대화: {{history}}

        사용자 입력: {{input}}

        답변:
        """
        ),
        1: ChatPromptTemplate.from_template(
            f"""
        너는 남중, 남고 출신의 거친 환경에서 함께 자란 {plantname}야.
        친구와 채팅 대화하는 것처럼 반말로 1~3문장으로 대화해.
        
        말투: 쌈싸한 말투

        이전 대화: {{history}}

        사용자 입력: {{input}}

        답변:
        """
        ),
    }
    return prompts.get(persona, prompts[0])


# =============================
# 메인 함수
# =============================
def communication_main():
    check_api_key()
    llm = initialize_llm()

    # 세션 스테이트 초기화 - 식물별 독립 관리
    if "comm_plant_messages" not in st.session_state:
        # 식물별로 메시지를 저장하는 딕셔너리 {식물이름: [메시지목록]}
        st.session_state.comm_plant_messages = {}
    if "comm_plant_persona" not in st.session_state:
        # 식물별로 페르소나를 저장하는 딕셔너리 {식물이름: 페르소나번호}
        st.session_state.comm_plant_persona = {}
    if "comm_plant" not in st.session_state:
        st.session_state.comm_plant = None
    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = False
    if "last_audio" not in st.session_state:
        st.session_state.last_audio = None

    # 메인에서 선택된 식물 반영
    if "selected_plant" in st.session_state and st.session_state["selected_plant"]:
        selected_plant = st.session_state["selected_plant"]
        
        # 식물이 변경되었는지 확인
        if st.session_state.comm_plant != selected_plant:
            st.session_state.comm_plant = selected_plant
            
            # 해당 식물의 메시지가 없으면 빈 리스트로 초기화
            if selected_plant not in st.session_state.comm_plant_messages:
                st.session_state.comm_plant_messages[selected_plant] = []
            
            # 해당 식물의 페르소나가 없으면 기본값(0) 설정
            if selected_plant not in st.session_state.comm_plant_persona:
                st.session_state.comm_plant_persona[selected_plant] = 0
    else:
        # ❗ 여기서: 이 페이지에서 식물이 선택되지 않았다면 홈으로 이동
        st.switch_page("app.py")
        st.stop()

    # 현재 식물 정보 가져오기
    plant_name = st.session_state.comm_plant
    persona = st.session_state.comm_plant_persona.get(plant_name, 0)
    messages = st.session_state.comm_plant_messages.get(plant_name, [])
    persona_label = "🌸 부드러운 친구" if persona == 0 else "💪 쌈싸한 친구"

    # 상단 정보 및 컨트롤
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(
            f"""
            <div style="padding:16px; background:#f0f7f4; border-radius:12px; margin-bottom:20px;">
                <div style="font-size:20px; font-weight:700; color:#2f6f3e;">
                    🌱 {plant_name}
                </div>
                <div style="font-size:13px; color:#666; margin-top:4px;">
                    {persona_label} 모드로 대화 중
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    with col2:
        voice_toggle = st.toggle("🔊 음성 답변", value=st.session_state.voice_enabled)
        st.session_state.voice_enabled = voice_toggle

    # 체인 준비 (식물별로 다른 session_id 사용)
    chain = build_chain(persona, plant_name, llm)

    # 대화 기록 표시
    chat_container = st.container()
    with chat_container:
        if len(messages) == 0:
            st.markdown(
                f"""
            <div style="text-align:center; padding:40px 20px; color:#7c7c7c;">
                <div style="font-size:18px; font-weight:600; margin-bottom:8px;">
                    👋 안녕! 나는 {plant_name}야. 편하게 대화해보자!
                </div>
                <div style="font-size:14px; margin-top:8px;">
                    💡 텍스트 입력 또는 🎤 버튼을 눌러 음성으로 대화할 수 있어요!
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            for message in messages:
                if message["role"] == "user":
                    st.markdown(
                        f"""
                    <div class="message-right">
                        <div class="bubble">{message["content"]}</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                    <div class="message-left">
                        <div class="avatar">🌱</div>
                        <div class="bubble">{message["content"]}</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    
                    # 음성 답변이 활성화되어 있고, 음성 데이터가 있으면 오디오 플레이어 표시
                    if st.session_state.voice_enabled and "audio" in message:
                        audio_html = create_audio_player(message["audio"])
                        st.markdown(audio_html, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

    # 하단 여백 확보
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)

    # 사용자 입력 영역
    input_col1, input_col2 = st.columns([6, 1])
    
    with input_col1:
        user_input = st.chat_input("메시지를 입력하세요...")
    
    with input_col2:
        # 음성 녹음 버튼 (패키지가 설치된 경우만)
        audio_bytes = None
        if AUDIO_RECORDER_AVAILABLE:
            audio_bytes = audio_recorder(
                text="",
                recording_color="#e74c3c",
                neutral_color="#6aa36f",
                icon_name="microphone",
                icon_size="2x",
            )
        else:
            st.info("🎤")  # 플레이스홀더

    # 텍스트 입력 처리
    if user_input:
        # UI 렌더링용 기록 (식물별 메시지 리스트에 추가)
        st.session_state.comm_plant_messages[plant_name].append({"role": "user", "content": user_input})

        with st.spinner(""):
            # RunnableWithMessageHistory가 질문/응답을 history에 자동 저장
            # 식물별로 다른 session_id 사용
            session_id = f"plant_{plant_name}"
            response = chain.invoke(
                {"input": user_input},
                config={"configurable": {"session_id": session_id}},
            )

        # AI 메시지 데이터 준비
        message_data = {"role": "assistant", "content": response}
        
        # 음성 답변이 활성화된 경우 TTS 실행하고 오디오 데이터 저장
        if st.session_state.voice_enabled:
            audio_data = text_to_speech(response)
            if audio_data:
                message_data["audio"] = audio_data
        
        st.session_state.comm_plant_messages[plant_name].append(message_data)
        st.rerun()

    # 음성 입력 처리
    if audio_bytes:
        # 세션에 저장된 마지막 오디오와 비교 (중복 처리 방지)
        if st.session_state.last_audio != audio_bytes:
            st.session_state.last_audio = audio_bytes
            
            with st.spinner("음성 인식 중..."):
                # BytesIO로 변환
                audio_file = BytesIO(audio_bytes)
                audio_file.name = "recorded_audio.wav"
                
                # STT 처리
                transcribed_text = speech_to_text(audio_file)
                
                if transcribed_text:
                    # 사용자 메시지 추가 (식물별 메시지 리스트에 추가)
                    st.session_state.comm_plant_messages[plant_name].append({"role": "user", "content": transcribed_text})
                    
                    # AI 응답 생성
                    session_id = f"plant_{plant_name}"
                    response = chain.invoke(
                        {"input": transcribed_text},
                        config={"configurable": {"session_id": session_id}},
                    )
                    
                    # AI 메시지 데이터 준비
                    message_data = {"role": "assistant", "content": response}
                    
                    # 음성 답변이 활성화된 경우 TTS 실행하고 오디오 데이터 저장
                    if st.session_state.voice_enabled:
                        audio_data = text_to_speech(response)
                        if audio_data:
                            message_data["audio"] = audio_data
                    
                    st.session_state.comm_plant_messages[plant_name].append(message_data)
                    st.rerun()

    # 하단 버튼
    if len(messages) > 0:
        st.markdown("---")
        st.markdown(
            """
        <style>
        .home-button { display: block; padding: 0.5rem 1rem; background-color: #2f6f3e; color: white !important; text-align: center; text-decoration: none !important; border-radius: 0.5rem; font-weight: 600; transition: all 0.2s; }
        .home-button:hover { background-color: #265a32; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(47, 111, 62, 0.3); }
        </style>
        """,
            unsafe_allow_html=True,
        )
        
        # 홈 버튼 클릭 시 세션 초기화
        if st.button("🏠 홈으로 돌아가기", key="home_button", use_container_width=True):
            # selected_plant 세션 초기화
            if "selected_plant" in st.session_state:
                del st.session_state["selected_plant"]
            # comm_plant 초기화
            st.session_state.comm_plant = None
            # 페이지 이동
            st.switch_page("app.py")


# =============================
# 메인 실행
# =============================
if __name__ == "__main__":
    communication_main()
