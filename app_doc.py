"""
식물 병해충 진단 챗봇
- 챗봇 형태의 대화형 인터페이스
- 비동기 작물 데이터 수집
- ngrok을 통한 외부 접속
"""

import os
import time
import threading
import streamlit as st
from pathlib import Path
import dotenv

dotenv.load_dotenv()

from plant_doctor import (
    PlantDiseaseCollector,
    PlantDiseaseRAG,
    TextPreprocessor
)

# ===== 페이지 설정 =====
st.set_page_config(
    page_title="식물 주치의",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 사이드바 완전 제거 CSS
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="collapsedControl"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# ===== 환경 변수 =====
NCPMS_API_KEY = os.getenv("NCPMS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("[오류] OPENAI_API_KEY 환경변수를 설정해 주세요.")
    st.stop()

# ===== 세션 상태 초기화 함수 =====
def init_session_state():
    """세션 상태 초기화"""
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

# ===== 시스템 초기화 =====
@st.cache_resource
def init_systems():
    """시스템 초기화"""
    collector = PlantDiseaseCollector(api_key=NCPMS_API_KEY)
    rag_system = PlantDiseaseRAG(openai_api_key=OPENAI_API_KEY)
    return collector, rag_system

collector, rag_system = init_systems()

# ===== 비동기 데이터 수집 함수 =====
def load_crop_data_background(crop_name):
    """백그라운드에서 작물 데이터 수집 (스레드 내부)"""
    try:
        # ChromaDB에 이미 있는지 확인
        chroma_dir = rag_system._get_chroma_dir(crop_name)
        if chroma_dir.exists():
            return {"status": "ready", "crop": crop_name}
        
        # 데이터 수집
        diseases = collector.collect_all_data(crop_name)
        
        if diseases:
            # ChromaDB 인덱스 생성
            rag_system.create_crop_index(crop_name, diseases)
            return {"status": "ready", "crop": crop_name}
        else:
            return {"status": "error", "crop": crop_name}
    except Exception as e:
        print(f"[오류] {crop_name} 데이터 로딩 실패: {e}")
        return {"status": "error", "crop": crop_name}

def check_crop_loading_status():
    """작물 로딩 상태 확인 및 업데이트"""
    # 로딩 중인 작물이 있는지 확인
    for crop_name in list(st.session_state.crop_loading.keys()):
        if st.session_state.crop_loading[crop_name]:
            # ChromaDB 확인
            chroma_dir = rag_system._get_chroma_dir(crop_name)
            if chroma_dir.exists():
                st.session_state.crop_data[crop_name] = "ready"
                st.session_state.crop_loading[crop_name] = False
                
                # 현재 작물이 준비되면 메시지 추가
                if st.session_state.current_crop == crop_name:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"'{crop_name}' 데이터 준비가 완료되었습니다!"
                    })
                    
                    # 대기 중인 증상이 있으면 자동 진단
                    if st.session_state.pending_symptom:
                        symptom = st.session_state.pending_symptom
                        st.session_state.pending_symptom = None
                        perform_diagnosis(symptom)

# ===== 작물 선택 함수 =====
def select_crop(crop_name):
    """작물 선택 및 데이터 로딩 시작"""
    st.session_state.current_crop = crop_name
    st.session_state.show_crop_selection = False
    
    # ChromaDB에 이미 있는지 확인
    chroma_dir = rag_system._get_chroma_dir(crop_name)
    if chroma_dir.exists():
        st.session_state.crop_data[crop_name] = "ready"
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"'{crop_name}'을(를) 선택하셨습니다.\n\n어떤 증상이 나타나고 있나요? 자세히 설명해주세요."
        })
        st.session_state.waiting_for_diagnosis = True
        return
    
    # 백그라운드에서 데이터 로딩 시작
    if crop_name not in st.session_state.crop_loading or not st.session_state.crop_loading.get(crop_name, False):
        st.session_state.crop_loading[crop_name] = True
        st.session_state.crop_data[crop_name] = "loading"
        
        # 스레드 시작 (session_state는 직접 접근하지 않음)
        thread = threading.Thread(target=load_crop_data_background, args=(crop_name,))
        thread.daemon = True
        thread.start()
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"'{crop_name}' 데이터를 준비하고 있습니다...\n\n데이터가 준비되는 동안 어떤 증상이 있는지 미리 입력해주세요!"
        })
        st.session_state.waiting_for_diagnosis = True

# ===== 진단 수행 함수 =====
def perform_diagnosis(symptom_text):
    """증상 기반 진단 수행"""
    crop_name = st.session_state.current_crop
    
    # 작물이 선택되지 않음
    if not crop_name:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "먼저 작물을 선택해주세요."
        })
        st.session_state.show_crop_selection = True
        return
    
    # ChromaDB 파일 시스템 직접 체크
    chroma_dir = rag_system._get_chroma_dir(crop_name)
    
    # 데이터가 준비되지 않음
    if not chroma_dir.exists():
        # 로딩 상태가 아니면 로딩 시작
        if not st.session_state.crop_loading.get(crop_name, False):
            st.session_state.crop_loading[crop_name] = True
            st.session_state.crop_data[crop_name] = "loading"
            
            thread = threading.Thread(target=load_crop_data_background, args=(crop_name,))
            thread.daemon = True
            thread.start()
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"'{crop_name}' 데이터를 준비 중입니다. 잠시만 기다려주세요..."
        })
        return
    
    # 데이터 준비 완료 - 상태 업데이트
    st.session_state.crop_data[crop_name] = "ready"
    st.session_state.crop_loading[crop_name] = False
    
    # 진단 수행
    try:
        similar_diseases = rag_system.search_similar_diseases(
            crop_name=crop_name,
            problem_text=symptom_text,
            top_k=3
        )
        
        if not similar_diseases:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "유사한 병해충을 찾지 못했습니다. 증상을 다르게 설명해주시겠어요?"
            })
            return
        
        # 결과 메시지 생성
        result_msg = f"'{crop_name}'에서 다음 병해충이 의심됩니다:"
        
        st.session_state.similar_diseases = similar_diseases
        
        # 이미지와 함께 결과 표시
        st.session_state.messages.append({
            "role": "assistant",
            "content": result_msg,
            "diseases": similar_diseases
        })
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"진단 중 오류가 발생했습니다: {str(e)}\n\n다시 시도해주세요."
        })

# ===== 상세 정보 조회 함수 =====
def get_disease_detail(disease_name):
    """선택된 병해충의 상세 정보 조회"""
    answer = rag_system.get_disease_detail_answer(
        crop_name=st.session_state.current_crop,
        disease_name=disease_name
    )
    
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"**{disease_name}** 상세 정보:\n\n{answer}"
    })

# ===== 메인 UI =====
def main():
    # 세션 상태 초기화 (가장 먼저 실행)
    init_session_state()
    
    # 헤더와 초기화 버튼
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("식물 주치의")
    with col2:
        st.write("")
        if st.button("대화 초기화", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_crop = None
            st.session_state.waiting_for_diagnosis = False
            st.session_state.similar_diseases = []
            st.session_state.show_crop_selection = True
            st.rerun()
    
    st.divider()
    
    # 작물 로딩 상태 체크
    check_crop_loading_status()
    
    # 초기 인사말
    if len(st.session_state.messages) == 0:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "안녕하세요! 식물 주치의입니다.\n\n진단하고 싶은 작물을 선택해주세요."
        })
        st.session_state.show_crop_selection = True
    
    # 채팅 메시지 표시
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # 병해충 결과가 있으면 이미지와 함께 표시
            if "diseases" in message:
                cols = st.columns(3)
                for i, (disease_name, score, content, image_path) in enumerate(message["diseases"]):
                    with cols[i]:
                        # 이미지
                        if image_path and Path(image_path).exists():
                            st.image(image_path, use_container_width=True)
                        else:
                            st.markdown(
                                """
                                <div style="
                                    width: 100%;
                                    height: 150px;
                                    background-color: #f0f0f0;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    border-radius: 10px;
                                ">
                                    <p style="color: #999;">이미지 없음</p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        
                        st.caption(f"{i+1}. {disease_name}")
                        st.caption(f"유사도: {(score*100):.2f}%")
                        
                        if st.button("이거에요!!", key=f"detail_{idx}_{i}", use_container_width=True):
                            get_disease_detail(disease_name)
                            st.rerun()
    
    # 작물 선택 버튼 표시
    if st.session_state.show_crop_selection:
        with st.chat_message("assistant"):
            st.write("진단할 작물을 선택하세요:")
            cols = st.columns(3)
            supported_crops = rag_system.get_supported_crops()
            
            for i, crop in enumerate(supported_crops):
                with cols[i % 3]:
                    # 로딩 상태에 따른 버튼 표시
                    if st.session_state.crop_loading.get(crop, False):
                        st.button(f"⏳ {crop}", disabled=True, use_container_width=True, key=f"select_{crop}")
                    else:
                        if st.button(crop, use_container_width=True, key=f"select_{crop}"):
                            select_crop(crop)
                            st.rerun()
    
    # 채팅 입력
    if prompt := st.chat_input("증상을 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 진단 수행
        if st.session_state.waiting_for_diagnosis:
            # ChromaDB가 준비되었는지 확인
            crop_name = st.session_state.current_crop
            if crop_name:
                chroma_dir = rag_system._get_chroma_dir(crop_name)
                if chroma_dir.exists():
                    # 즉시 진단
                    perform_diagnosis(prompt)
                else:
                    # 준비 중이면 증상을 저장하고 대기
                    st.session_state.pending_symptom = prompt
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "데이터 준비 중입니다. 곧 진단을 시작하겠습니다..."
                    })
            else:
                perform_diagnosis(prompt)
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "먼저 작물을 선택해주세요."
            })
            st.session_state.show_crop_selection = True
        
        st.rerun()
    
    # 로딩 중인 작물이 있으면 자동 갱신
    if any(st.session_state.crop_loading.get(crop, False) for crop in st.session_state.crop_loading):
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    main()