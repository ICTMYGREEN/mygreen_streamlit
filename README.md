📢 **본 프로젝트는 2025년 ICT 이노베이션스퀘어 확산사업 · 위니브 주관 AI Chatbot & RAG 해커톤 출품작입니다.**

# MYGREEN 🌱

## 📋 프로젝트 개요

**MYGREEN**은 식물 재배자를 위한 종합 AI 관리 플랫폼으로, RAG 기반 병해충 진단, 음성 대화형 인터페이스, 감정 기반 재배 일지 작성 등 혁신적인 기능을 제공하는 Streamlit 웹 애플리케이션입니다.

---

## 주요 기능

### 1. 홈 (식물 관리 대시보드)

**통합 식물 관리 시스템**
- **멀티 플랜트 관리**: 여러 식물을 동시에 관리하고 추적
- **실시간 통계 표시**:
  - 재배 일수 자동 계산 (심은 날짜부터 현재까지)
  - 마지막 일지 작성 날짜 표시
  - 총 작성된 일지 개수
  - 감정 점수 평균 및 추이
- **PDF 일지 책자 생성**:
  - 식물별 모든 일지를 아름다운 책자 형태로 변환
  - 한글 폰트 자동 감지 및 적용
  - 표지, 목차, 본문, 통계 페이지 포함
  - A4 사이즈, 페이지 번호 자동 생성
- **반응형 카드 UI**: 식물별 정보를 직관적인 카드 형태로 표시

**구현 세부사항**:
```python
# app.py
- calculate_days_since(): 재배 일수 실시간 계산
- get_plant_info(): 식물별 통계 데이터 집계
- plant_card(): 동적 카드 UI 렌더링
- generate_pdf(): ReportLab 기반 PDF 생성
```

### 2. 식물 병원 (AI 병해충 진단 시스템)

**RAG 기반 지능형 진단 시스템**

#### 핵심 기술 스택
- **Vector Database**: ChromaDB를 활용한 영구 저장소
- **Embeddings**: OpenAI text-embedding-3-small 모델
- **LLM**: GPT-4o-mini를 통한 자연어 이해 및 응답 생성
- **Data Source**: NCPMS (농촌진흥청 농작물병해충관리시스템) API

#### 진단 프로세스

**1단계: 데이터 수집 및 벡터화**
```python
# plant_doctor.py - PlantDiseaseCollector 클래스
def collect_all_data(crop_name):
    # NCPMS API 호출
    1. get_crop_diseases(): 작물별 병해충 목록 조회 (serviceCode=SVC01)
    2. get_disease_detail(): 각 병해충 상세 정보 조회 (serviceCode=SVC05)
       - 병명 (sickNameKor)
       - 발생생태 (developmentCondition)
       - 증상 (symptoms)
       - 방제방법 (preventionMethod)
    3. save_disease_image(): 병해충 이미지 다운로드 및 저장
       - noImg 체크 및 필터링
       - ./crop_images/{작물명}/{병명}.png 형태로 저장
```

**2단계: 벡터 인덱싱**
```python
# plant_doctor.py - PlantDiseaseRAG 클래스
def create_crop_index(crop_name, diseases):
    1. TextPreprocessor로 텍스트 정제
       - 한글, 영문, 숫자, 공백만 유지
       - HTML 태그 제거
       - 연속 공백 제거
    2. OpenAIEmbeddings로 벡터 변환
    3. ChromaDB persistent storage에 저장
       - ./chroma_db/{작물명}/ 디렉토리
       - 메타데이터: 병명, 증상, 발생생태, 방제방법, 이미지 경로
```

**3단계: 실시간 진단**
```python
# app_doc.py - diagnose_disease()
def diagnose_disease(crop, symptom):
    1. 증상 텍스트 전처리
    2. 유사도 검색 (Top-K=3)
       - 코사인 유사도 계산
       - 가장 유사한 병해충 3개 추출
    3. GPT-4o-mini를 통한 상세 분석
       - 원인 분석
       - 증상 설명
       - 방제 방법 제공
    4. 이미지와 함께 결과 표시
```

#### 비동기 데이터 로딩
```python
# app_doc.py - load_crop_data_async()
- threading.Thread를 사용한 백그라운드 로딩
- 사용자는 데이터 로딩 중에도 증상 입력 가능
- 진행률 표시 (st.progress)
- 에러 핸들링 및 재시도 로직
```

**성능 최적화**:
- ChromaDB persistent storage로 한 번 수집한 데이터 재사용
- @st.cache_resource를 통한 시스템 초기화 캐싱
- 비동기 로딩으로 사용자 대기 시간 최소화

### 3. 대화 하기 (식물과의 음성 대화)

**인터랙티브 음성 채팅 시스템**

#### 핵심 기능
- **음성 입력**: audio_recorder_streamlit 기반 실시간 녹음
- **음성 인식**: OpenAI Whisper API를 통한 STT (Speech-to-Text)
- **대화형 AI**: GPT-4o-mini 기반 자연어 대화
- **음성 출력**: OpenAI TTS API를 통한 음성 합성 (alloy 모델)
- **대화 기억**: LangChain InMemoryChatMessageHistory로 컨텍스트 유지

#### 식물별 페르소나 시스템
```python
# pages/voice_chat.py - get_plant_prompt()
식물별 맞춤 프롬프트:
- 토마토: 밝고 활기찬 성격, 햇빛과 물 사랑
- 장미: 우아하고 세련된 말투, 아름다움 추구
- 선인장: 강인하고 차분한 성격, 건조한 환경 선호
- 허브: 실용적이고 친근한 성격, 요리와 향기에 관심
- 다육이: 귀엽고 사랑스러운 말투, 물 절약형
```

#### 대화 관리
```python
# RunnableWithMessageHistory 사용
- 식물별 독립적인 대화 세션 관리
- session_id: "plant_{식물명}" 형태로 구분
- 대화 히스토리 메모리 저장
- 컨텍스트 기반 연속 대화 지원
```

#### UI/UX 특징
- **카카오톡 스타일 채팅 UI**:
  - 사용자 메시지: 오른쪽 정렬 (파란색 말풍선)
  - AI 메시지: 왼쪽 정렬 (연두색 말풍선)
  - 식물 아바타 이모지 표시
- **음성 플레이어**:
  - 자동재생 옵션
  - Base64 인코딩 audio HTML player
- **반응형 레이아웃**: 모바일/데스크톱 대응

### 4. 일지 작성 (MindCoach - 감정 기반 일지 시스템)

**RAG 기반 감정 분석 및 맞춤형 조언 시스템**

#### 이중 RAG 아키텍처
```python
# mind_coach.py - MindCoachRAG 클래스
1. High Emotion RAG (긍정 감정)
   - 긍정적 감정 상태 관련 문서 임베딩
   - 축하, 격려, 성취감 강화 조언
   
2. Low Emotion RAG (부정 감정)
   - 부정적 감정 상태 관련 문서 임베딩
   - 위로, 해결책, 극복 방법 조언
```

#### 감정 분석 프로세스
```python
def analyze_emotion(diary_text):
    1. 일지 내용 분석
    2. 감정 점수 산출 (0-10점)
       - 0-3: 매우 부정적
       - 4-6: 중립/혼재
       - 7-10: 긍정적
    3. 주요 감정 단어 추출
    4. 감정 상태 설명
```

#### 맞춤형 조언 생성
```python
def get_plant_advice(diary_text, emotion_data):
    1. 감정 점수에 따라 적절한 RAG DB 선택
       - 점수 ≥ 6: High Emotion RAG
       - 점수 < 6: Low Emotion RAG
    2. 유사도 검색으로 관련 조언 추출 (Top-3)
    3. GPT-4o-mini로 개인화된 조언 생성
    4. 식물 성장과 연결된 메시지 제공
```

#### 일지 저장 및 관리
```python
# diary_storage.py - DiaryStorage 클래스
- CSV 기반 영구 저장 (./diary_data/diaries.csv)
- 저장 데이터:
  * plant_name: 식물 이름
  * date: 작성 날짜
  * planted_date: 심은 날짜
  * diary: 일지 내용
  * emotion_score: 감정 점수 (0-10)
  * advice: AI 조언
  * timestamp: 생성 시각
```

#### 통계 및 분석
```python
def get_statistics(plant_name):
    - 총 일지 수
    - 평균 감정 점수
    - 최고/최저 감정 점수
    - 긍정적 일지 비율
    - 시간대별 감정 추이
```

#### UI 기능
- **일지 작성 폼**:
  - 식물 이름 입력
  - 심은 날짜 선택
  - 일지 내용 작성 (텍스트 영역)
  - 실시간 감정 분석 및 조언 생성
- **일지 목록**:
  - 식물별 필터링
  - 날짜순 정렬
  - 감정 점수 시각화 (색상 코딩)
  - 삭제 기능
- **통계 대시보드**:
  - 식물별 성장 추이
  - 감정 점수 그래프
  - 요약 통계

---

## 프로젝트 구조

```
streamlit_MYGREEN/
├── app.py                      # 메인 애플리케이션 (홈 화면)
│   ├── start_ngrok()          # Ngrok 터널 관리
│   ├── get_storage()          # DiaryStorage 싱글톤
│   ├── calculate_days_since() # 재배 일수 계산
│   ├── generate_pdf()         # PDF 생성 로직
│   └── plant_card()           # 식물 카드 UI 렌더링
│
├── app_doc.py                  # 식물 병원 챗봇 로직
│   ├── init_session_state()   # 세션 상태 초기화
│   ├── load_crop_data_async() # 비동기 데이터 로딩
│   ├── diagnose_disease()     # RAG 기반 진단
│   └── main()                 # 챗봇 UI 렌더링
│
├── plant_doctor.py             # RAG 시스템 및 데이터 수집
│   ├── PlantDiseaseCollector  # NCPMS API 연동
│   │   ├── get_crop_diseases()    # 병해충 목록 조회
│   │   ├── get_disease_detail()   # 상세 정보 조회
│   │   ├── save_disease_image()   # 이미지 저장
│   │   └── collect_all_data()     # 전체 수집 파이프라인
│   │
│   └── PlantDiseaseRAG         # RAG 시스템
│       ├── create_crop_index()    # 벡터 인덱싱
│       ├── search_diseases()      # 유사도 검색
│       └── generate_diagnosis()   # LLM 진단 생성
│
├── mind_coach.py               # 감정 분석 RAG 시스템
│   └── MindCoachRAG
│       ├── initialize_vector_dbs() # 이중 RAG 초기화
│       ├── analyze_emotion()       # 감정 점수 산출
│       ├── get_plant_advice()      # 맞춤형 조언 생성
│       └── get_full_response()     # 통합 응답
│
├── diary_storage.py            # 일지 저장소 관리
│   └── DiaryStorage
│       ├── save_diary()          # 일지 저장
│       ├── get_plant_diaries()   # 식물별 조회
│       ├── get_statistics()      # 통계 계산
│       └── delete_diary()        # 삭제
│
├── diary_pdf.py               # PDF 생성 기능
│   └── DiaryPDFMaker
│       ├── _register_fonts()     # 한글 폰트 등록
│       ├── create_cover()        # 표지 생성
│       ├── create_toc()          # 목차 생성
│       ├── create_diary_page()   # 일지 페이지
│       └── create_statistics()   # 통계 페이지
│
├── pages/                      # Streamlit 멀티페이지
│   ├── plantdoc.py            # 식물 병원 페이지 (app_doc 임포트)
│   ├── mindcoach.py           # 일지 작성 페이지 (UI + 폼)
│   └── voice_chat.py          # 음성 대화 페이지
│       ├── get_plant_prompt()    # 식물별 페르소나
│       ├── text_to_speech()      # TTS 변환
│       └── transcribe_audio()    # STT 변환
│
├── chroma_db/                  # ChromaDB 벡터 데이터베이스
│   ├── crop_{작물코드}/
│   ├── crop_fl22402/
│   ├── crop_fl02242/
│   └── ...                    # 기타 작물별 디렉토리
│
├── mind_db/                    # MindCoach RAG 데이터베이스
│   ├── high_emotion/          # 긍정 감정 DB
│   └── low_emotion/           # 부정 감정 DB
│
├── crop_images/               # 병해충 이미지
│   ├── 작물_{병명}/
│   ├── 국화_녹병.png/
│   └── ...
│
├── diary_data/                # 일지 CSV 저장소
│   └── diaries.csv
│
├── diary_pdfs/                # 생성된 PDF 파일
│
├── data/                      # MindCoach 학습 데이터
│   ├── high_emotion.pdf
│   └── low_emotion.pdf
│
├── .env                       # 환경 변수 설정
├── .gitignore                 # Git 제외 파일
├── requirements.txt           # Python 패키지 의존성
└── README.md                  # 프로젝트 문서
```

---

## 🛠️ 기술 스택

### Backend & Core
- **Python 3.12+** - 메인 언어
- **Streamlit 1.29+** - 웹 애플리케이션 프레임워크
- **LangChain** - LLM 오케스트레이션 및 체인 구성
- **LangChain-OpenAI** - OpenAI 모델 통합

### AI & ML
- **OpenAI GPT-4o-mini** - 자연어 이해, 대화, 진단 생성
- **OpenAI Embeddings** - text-embedding-3-small 모델
- **OpenAI Whisper** - 음성 인식 (STT)
- **OpenAI TTS** - 음성 합성 (alloy 모델)

### RAG & Vector Database
- **ChromaDB** - 영구 벡터 데이터베이스
- **Persistent Storage** - 디스크 기반 벡터 인덱스

### Data Sources
- **NCPMS API** (농촌진흥청 농작물병해충관리시스템)
  - 작물 병해충 데이터
  - 증상, 발생생태, 방제방법
  - 병해충 이미지

### Data Processing
- **Pandas** - 데이터프레임 처리 및 분석
- **Python-dotenv** - 환경 변수 관리
- **Requests** - HTTP API 호출

### UI & UX
- **Streamlit Audio Recorder** - 실시간 음성 녹음
- **Base64 Encoding** - 오디오 스트리밍
- **Custom CSS** - 카카오톡 스타일 채팅 UI

### PDF Generation
- **ReportLab** - PDF 문서 생성
- **Pillow (PIL)** - 이미지 처리
- **TTF Fonts** - 한글 폰트 지원

### Deployment
- **Pyngrok** - 로컬 서버 외부 공개
- **Threading** - 비동기 백그라운드 작업

---

## ⚙️ 설치 및 실행

### 1. 환경 설정

```bash
# 가상환경 생성 (권장)
conda create -n MYGREEN python=3.12
conda activate MYGREEN

# 또는 venv 사용
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 패키지 설치

```bash
# 필수 패키지
pip install streamlit==1.29.0
pip install openai==1.3.0
pip install langchain==0.1.0
pip install langchain-community==0.0.10
pip install langchain-openai==0.0.2
pip install chromadb==0.4.18
pip install python-dotenv==1.0.0
pip install pandas==2.1.4
pip install pillow==10.1.0
pip install reportlab==4.0.7
pip install pyngrok==7.0.0
pip install requests==2.31.0

# 음성 기능 (선택)
pip install audio-recorder-streamlit==0.0.8
```

또는 `requirements.txt`가 있다면:

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 입력:

```env
# OpenAI API Key (필수)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# NCPMS API Key (선택 - 병해충 데이터 수집 시 필요)
NCPMS_API_KEY=your-ncpms-api-key

# Ngrok Auth Token (외부 접속 시 필요)
NGROK_AUTHTOKEN=your-ngrok-token-here
```

**API 키 발급 방법**:
- **OpenAI**: https://platform.openai.com/api-keys
- **NCPMS**: http://ncpms.rda.go.kr (회원가입 후 발급)
- **Ngrok**: https://dashboard.ngrok.com/get-started/your-authtoken

### 4. 애플리케이션 실행

```bash
# 메인 앱 실행
streamlit run app.py

# 특정 포트 지정
streamlit run app.py --server.port 8501

# 외부 접속 허용
streamlit run app.py --server.address 0.0.0.0
```

**실행 후 접속**:
- 로컬: http://localhost:8501
- Ngrok URL: 터미널에 표시된 공개 URL

---

## 🔧 주요 기능 상세 분석

### RAG 시스템 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                    사용자 입력                        │
│         "잎에 검은 반점과 노란 테두리가 생겼어요"       │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              텍스트 전처리 (TextPreprocessor)         │
│  - HTML 태그 제거 (<p>, <br> 등)                     │
│  - 한글/영문/숫자/공백만 유지                          │
│  - 연속 공백 정규화                                   │
│  - 특수문자 제거                                      │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│            OpenAI Embeddings                        │
│         text-embedding-3-small 모델                 │
│       증상 텍스트 → 1536차원 벡터로 변환              │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              ChromaDB 유사도 검색                     │
│  - 코사인 유사도 계산                                 │
│  - Top-K=3 추출                                      │
│  - 메타데이터: {병명, 증상, 발생생태, 방제방법, 이미지}│
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              GPT-4o-mini 응답 생성                    │
│  프롬프트 구성:                                       │
│  - 작물명: {선택한 작물}                              │
│  - 증상: {사용자 입력}                                │
│  - 유사 병해충 Top-3: {RAG 결과}                     │
│  응답 형식:                                          │
│  - 가능한 병해충 (확률 높은 순)                       │
│  - 원인 분석                                         │
│  - 증상 설명                                         │
│  - 방제 방법 (화학적/생물학적/물리적)                 │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│              결과 UI 렌더링                          │
│  - 병해충 이미지 표시 (st.image)                     │
│  - 진단 결과 텍스트 (st.markdown)                    │
│  - 추가 증상 입력 가능                                │
└─────────────────────────────────────────────────────┘
```

### 데이터 수집 파이프라인

```python
# plant_doctor.py 동작 흐름

1. NCPMS API 호출 (작물 선택)
   ├─> GET /service
   ├─> params: {apiKey, serviceCode: "SVC01", cropName}
   └─> Response: [{sickKey, sickNameKor, thumbImg}, ...]

2. 병해충별 상세 정보 조회 (비동기)
   ├─> GET /service
   ├─> params: {apiKey, serviceCode: "SVC05", sickKey}
   └─> Response: {
         sickNameKor: "탄저병",
         symptoms: "잎에 검은 반점...",
         developmentCondition: "고온다습...",
         preventionMethod: "살균제 살포...",
         thumbImg: "http://..."
       }

3. 이미지 다운로드 및 저장
   ├─> requests.get(thumbImg)
   ├─> Image.open(BytesIO(content))
   ├─> 파일명 정규화: "고추_탄저병.png"
   └─> 저장: ./crop_images/고추_탄저병.png

4. 텍스트 전처리
   ├─> HTML 태그 제거: re.sub(r'<[^>]+>', '', text)
   ├─> 한글/영문/숫자/공백만 유지: re.sub(r'[^가-힣a-zA-Z0-9\s]', '', text)
   └─> 연속 공백 정규화: re.sub(r'\s+', ' ', text)

5. 벡터 인덱싱 (ChromaDB)
   ├─> OpenAIEmbeddings 초기화
   ├─> Chroma.from_texts(
   │     texts=[병 증상 텍스트],
   │     embedding=embeddings,
   │     metadatas=[{병명, 발생생태, 방제방법, 이미지 경로}],
   │     persist_directory="./chroma_db/crop_{작물코드}"
   │   )
   └─> 디스크에 영구 저장

6. 검색 및 진단 (사용자 요청 시)
   ├─> vectorstore.similarity_search(증상, k=3)
   ├─> GPT-4o-mini로 컨텍스트 생성
   │     messages=[
   │       {"role": "system", "content": "당신은 농업 전문가..."},
   │       {"role": "user", "content": f"작물: {작물}, 증상: {증상}, 유사 병해충: {결과}"}
   │     ]
   └─> 진단 결과 및 이미지 반환
```

### 감정 분석 및 조언 생성 흐름

```python
# mind_coach.py - MindCoachRAG 클래스

1. 이중 RAG 초기화
   ├─> High Emotion RAG
   │   ├─> PDF 로드: ./data/high_emotion.pdf
   │   ├─> RecursiveCharacterTextSplitter (chunk_size=500, overlap=50)
   │   ├─> OpenAIEmbeddings 벡터화
   │   └─> ChromaDB 저장: ./mind_db/high_emotion/
   │
   └─> Low Emotion RAG
       ├─> PDF 로드: ./data/low_emotion.pdf
       ├─> RecursiveCharacterTextSplitter
       ├─> OpenAIEmbeddings 벡터화
       └─> ChromaDB 저장: ./mind_db/low_emotion/

2. 감정 분석 (analyze_emotion)
   ├─> GPT-4o-mini 프롬프트:
   │     "다음 일지를 읽고 감정 점수(0-10)를 매겨주세요.
   │      0: 매우 부정적, 10: 매우 긍정적
   │      JSON 형식: {score, keywords, description}"
   │
   ├─> 응답 파싱
   └─> 반환: {
         "score": 7,
         "keywords": ["뿌듯하다", "성장"],
         "description": "식물 성장을 보며 긍정적인 감정"
       }

3. 조언 생성 (get_plant_advice)
   ├─> 감정 점수 기반 RAG 선택
   │   ├─> score >= 6 → High Emotion RAG
   │   └─> score < 6 → Low Emotion RAG
   │
   ├─> 유사도 검색 (Top-3)
   │   vectorstore.similarity_search(일지 내용, k=3)
   │
   ├─> GPT-4o-mini 프롬프트:
   │     "일지: {일지 내용}
   │      감정 분석: {감정 데이터}
   │      참고 조언: {RAG 결과}
   │      
   │      식물 성장과 연결하여 따뜻한 조언을 작성하세요."
   │
   └─> 개인화된 조언 생성

4. 일지 저장 (diary_storage.py)
   ├─> DataFrame 생성/업데이트
   ├─> CSV 저장: ./diary_data/diaries.csv
   │     Columns: [plant_name, date, planted_date, diary, 
   │               emotion_score, advice, timestamp]
   └─> 자동 백업

5. PDF 생성 (diary_pdf.py)
   ├─> 한글 폰트 자동 감지
   │   Windows: malgun.ttf / batang.ttf
   │   Linux: NanumGothic.ttf
   │   Mac: AppleGothic.ttf
   │
   ├─> 페이지 구성
   │   ├─> 표지: 식물명, 기간, 총 일지 수
   │   ├─> 목차: 날짜별 인덱스
   │   ├─> 본문: 각 일지 전체 내용 + 감정 점수
   │   └─> 통계: 평균 점수, 긍정 비율, 추이 그래프
   │
   └─> A4 PDF 생성: ./diary_pdfs/{식물명}_일지_{날짜}.pdf
```

---

## 성능 최적화 전략

### 1. 캐싱 전략

```python
# Streamlit 리소스 캐싱
@st.cache_resource
def init_systems():
    """시스템 초기화 - 앱 전체에서 한 번만 실행"""
    collector = PlantDiseaseCollector(api_key=NCPMS_API_KEY)
    rag_system = PlantDiseaseRAG(openai_api_key=OPENAI_API_KEY)
    return collector, rag_system

@st.cache_resource
def get_storage():
    """DiaryStorage 싱글톤 - 데이터 로딩 최소화"""
    return DiaryStorage()
```

### 2. 비동기 데이터 로딩

```python
# app_doc.py - 백그라운드 데이터 수집
def load_crop_data_async(crop_name):
    def load_data():
        # NCPMS API 호출 및 ChromaDB 인덱싱
        collector.collect_all_data(crop_name)
        rag_system.create_crop_index(crop_name, diseases)
    
    # 별도 스레드에서 실행
    thread = threading.Thread(target=load_data)
    thread.start()
    
    # 사용자는 진행률 확인 가능
    progress_bar = st.progress(0)
    while thread.is_alive():
        # 진행 상태 업데이트
        progress_bar.progress(percent)
```

### 3. ChromaDB 영구 저장소

```python
# 한 번 수집한 데이터는 디스크에 저장되어 재사용
vectorstore = Chroma(
    persist_directory=f"./chroma_db/{crop_name}",
    embedding_function=embeddings
)

# 데이터 존재 여부 확인
if os.path.exists(f"./chroma_db/{crop_name}"):
    # 기존 데이터 로드 (API 호출 불필요)
    vectorstore = load_existing_db()
else:
    # 새로 수집
    collect_and_index()
```

### 4. 텍스트 전처리 최적화

```python
class TextPreprocessor:
    """정규식 패턴 캐싱으로 성능 향상"""
    
    def __init__(self):
        # 컴파일된 정규식 재사용
        self.html_pattern = re.compile(r'<[^>]+>')
        self.char_pattern = re.compile(r'[^가-힣a-zA-Z0-9\s]')
        self.space_pattern = re.compile(r'\s+')
    
    def clean(self, text):
        text = self.html_pattern.sub('', text)
        text = self.char_pattern.sub('', text)
        text = self.space_pattern.sub(' ', text)
        return text.strip()
```

### 5. 메모리 관리

```python
# 대용량 이미지 처리 시 메모리 효율성
def save_disease_image(crop_name, disease_name, img_url):
    response = requests.get(img_url, stream=True)  # 스트리밍 다운로드
    img = Image.open(BytesIO(response.content))
    img.save(filepath, optimize=True, quality=85)  # 압축 저장
    del img  # 명시적 메모리 해제
```

---

## 알려진 이슈 및 해결책

### 1. Session State 초기화 오류

**증상**:
```python
AttributeError: st.session_state has no attribute "crop_loading"
```

**원인**:
Streamlit 멀티페이지 앱에서 페이지 간 이동 시 세션 상태 초기화 순서 문제

**해결책**:
```python
# pages/plantdoc.py
import streamlit as st

# app_doc 임포트 전에 필수 세션 상태 미리 초기화
if 'crop_loading' not in st.session_state:
    st.session_state.crop_loading = False
if 'selected_crop' not in st.session_state:
    st.session_state.selected_crop = None

# 이제 안전하게 임포트
from app_doc import main

# app_doc.py
def init_session_state():
    """세션 상태 초기화 (멱등성 보장)"""
    defaults = {
        'crop_loading': False,
        'selected_crop': None,
        'crop_data_loaded': False,
        'messages': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
```

### 2. ChromaDB 의존성 충돌

**증상**:
```
ERROR: pydantic 2.5.0 requires pydantic_core>=2.14.0
ERROR: numpy version conflict
```

**원인**:
ChromaDB와 다른 패키지 간의 버전 호환성 문제

**해결책**:
```bash
# 순서대로 설치
pip uninstall -y chromadb pydantic numpy
pip install numpy==1.26.4
pip install pydantic==2.5.3
pip install chromadb==0.4.18
```

### 3. 한글 폰트 인식 실패

**증상**:
PDF에서 한글이 깨지거나 표시되지 않음

**해결책**:
```python
# diary_pdf.py - 다중 폰트 경로 시도
font_paths = [
    "C:/Windows/Fonts/malgun.ttf",      # Windows
    "C:/Windows/Fonts/batang.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
    "/System/Library/Fonts/AppleGothic.ttf",  # Mac
]

for font_path in font_paths:
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Korean', font_path))
        return
```

### 4. NCPMS API Rate Limiting

**증상**:
```
[오류] API 호출 실패: 429 Too Many Requests
```

**해결책**:
```python
import time

def get_disease_detail_with_retry(sick_key, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** attempt  # 지수 백오프
                time.sleep(wait_time)
                continue
            raise
```

### 5. 음성 녹음 실패 (브라우저 권한)

**증상**:
마이크 접근이 차단되거나 녹음이 되지 않음

---

## 배포

### 1. Ngrok를 통한 로컬 공개

```bash
# 1. Ngrok 설치
# Windows: choco install ngrok
# Mac: brew install ngrok
# Linux: sudo snap install ngrok

# 2. 인증 토큰 설정
ngrok config add-authtoken YOUR_AUTHTOKEN

# 3. Streamlit 앱 실행
streamlit run app.py

# 4. 별도 터미널에서 ngrok 실행
ngrok http 8501

# 또는 .env에 NGROK_AUTHTOKEN 설정하면 자동으로 터널 생성
```

**app.py에 내장된 자동 ngrok**:
```python
# ngrok가 자동으로 시작되며 공개 URL이 터미널에 출력됨
# 예: https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app
```

---

## 테스트

### 수동 테스트 시나리오

#### 1. 홈 화면 테스트
- [ ] 식물 카드가 정상적으로 표시되는가?
- [ ] 재배 일수가 정확하게 계산되는가?
- [ ] 마지막 일지 날짜가 올바른가?
- [ ] 감정 점수 평균이 정확한가?
- [ ] PDF 다운로드 버튼이 작동하는가?
- [ ] 생성된 PDF에 한글이 정상 표시되는가?
- [ ] PDF에 모든 일지가 포함되어 있는가?

#### 2. 식물 병원 테스트
- [ ] 작물 선택 시 데이터 로딩이 시작되는가?
- [ ] 진행률 표시가 업데이트되는가?
- [ ] 데이터 로딩 중에도 증상 입력이 가능한가?
- [ ] 증상 입력 후 진단 결과가 표시되는가?
- [ ] Top-3 병해충이 관련성이 있는가?
- [ ] 이미지가 정상적으로 로드되는가?
- [ ] 방제 방법이 구체적으로 제시되는가?
- [ ] 같은 작물 재선택 시 빠르게 로드되는가? (캐싱)

#### 3. 음성 대화 테스트
- [ ] 마이크 권한이 정상적으로 요청되는가?
- [ ] 음성 녹음이 가능한가?
- [ ] STT 변환이 정확한가? (한글 지원)
- [ ] AI 응답이 식물 페르소나에 맞는가?
- [ ] TTS 음성이 재생되는가?
- [ ] 대화 히스토리가 유지되는가?
- [ ] 식물 변경 시 대화가 초기화되는가?

#### 4. 일지 작성 테스트
- [ ] 식물 이름, 심은 날짜, 일지 내용이 저장되는가?
- [ ] 감정 분석이 정확한가? (0-100점)
- [ ] AI 조언이 감정 상태에 맞는가?
- [ ] 긍정적 일지 vs 부정적 일지 조언 차이가 있는가?
- [ ] 일지 목록이 날짜순으로 정렬되는가?
- [ ] 식물별 필터링이 작동하는가?

---

## 📝 개발 로드맵

### 현재 버전 (v1.0) ✅
- ✅ 식물 관리 대시보드
- ✅ RAG 기반 병해충 진단
- ✅ 음성 대화 시스템 (STT/TTS)
- ✅ 감정 분석 기반 일지 작성
- ✅ PDF 책자 자동 생성
- ✅ ChromaDB 영구 저장소
- ✅ Ngrok 외부 접속

### 계획 중인 기능 (v2.0) 🚧
- [ ] **이미지 기반 병해충 진단**
  - OpenAI Vision API 또는 Custom CNN 모델
  - 사진 업로드로 즉시 진단
  - 증상 심각도 평가 (경미/중간/심각)

- [ ] **IoT 디바이스 연동**
  - 토양 습도, 온도, 조도 센서 데이터 수집
  - 자동 물주기 알림
  - 환경 데이터 기반 성장 예측

### 기술 부채 개선 (v1.5) 🔧
- [ ] 단위 테스트 커버리지 80% 이상
- [ ] CI/CD 파이프라인 구축 (GitHub Actions)
- [ ] 에러 로깅 및 모니터링 (Sentry)
- [ ] 데이터베이스 마이그레이션 (CSV → SQLite/PostgreSQL)
- [ ] API 응답 캐싱 (Redis)

---

## 🤝 기여 가이드

### Pull Request 프로세스

1. **Fork the repository**
   ```bash
   gh repo fork greenation/mygreen
   ```

2. **Create your feature branch**
   ```bash
   git checkout -b feature/AmazingFeature
   ```

3. **Commit your changes**
   ```bash
   git commit -m 'feat: Add some AmazingFeature'
   ```
   
   **Commit 컨벤션**:
   - `feat`: 새로운 기능
   - `fix`: 버그 수정
   - `docs`: 문서 업데이트
   - `style`: 코드 포맷팅
   - `refactor`: 코드 리팩토링
   - `test`: 테스트 추가/수정
   - `chore`: 빌드/설정 변경

4. **Push to the branch**
   ```bash
   git push origin feature/AmazingFeature
   ```

5. **Open a Pull Request**
   - PR 템플릿에 따라 작성
   - 스크린샷/동영상 첨부 (UI 변경 시)
   - 관련 이슈 링크

### 코딩 스타일

```python
# PEP 8 준수
# 함수/변수명: snake_case
# 클래스명: PascalCase
# 상수: UPPER_CASE

# 타입 힌트 사용 권장
def process_diary(plant_name: str, content: str) -> Dict[str, Any]:
    """일지 처리 및 감정 분석
    
    Args:
        plant_name: 식물 이름
        content: 일지 내용
    
    Returns:
        감정 분석 결과 딕셔너리
    """
    pass

# Docstring 작성 (Google Style)
```

---

## 📄 라이선스

이 프로젝트는 **MIT 라이선스** 하에 배포됩니다.

```
MIT License

Copyright (c) 2025 MYGREEN Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 팀 정보

**MYGREEN Team**

**개발 스택 전문성**:
- AI/ML: RAG, LangChain, OpenAI API
- Backend: Python, Streamlit, Vector DB
- Data: Pandas, ChromaDB, NCPMS API
- DevOps: Ngrok


---

## 감사의 글

### 데이터 제공
- **NCPMS** (농촌진흥청 농작물병해충관리시스템)
  - 20개 작물, 300+ 병해충 데이터
  - 고해상도 이미지 및 상세 방제 정보
  - API 무료 제공

### 기술 지원
- **OpenAI**
  - GPT-4o-mini 모델
  - Embeddings API (text-embedding-3-small)
  - Whisper STT / TTS API

- **ChromaDB**
  - 오픈소스 벡터 데이터베이스
  - 영구 저장소 기능
  - 빠른 유사도 검색

- **LangChain**
  - RAG 파이프라인 구축 프레임워크
  - 대화 히스토리 관리
  - 프롬프트 템플릿

- **Streamlit**
  - 빠른 웹 앱 프로토타이핑
  - 멀티페이지 지원
  - 간편한 배포 (Streamlit Cloud)

### 해커톤 주최
- **ICT 이노베이션스퀘어 확산사업**
- **위니브 (WENIV)**
  - AI Chatbot & RAG 해커톤 2025
  - 멘토링 및 기술 지원

---

## 참고 자료

### API 문서
- [NCPMS API 가이드](http://ncpms.rda.go.kr/npmsAPI/openApiGuide.do)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [ChromaDB Documentation](https://docs.trychroma.com)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)

### 기술 블로그
- [RAG 시스템 구축 완벽 가이드](https://www.langchain.com/rag)
- [Streamlit 멀티페이지 앱 개발](https://docs.streamlit.io/library/advanced-features/multipage-apps)
- [OpenAI Embeddings 최적화](https://platform.openai.com/docs/guides/embeddings)
- [ChromaDB 성능 튜닝](https://docs.trychroma.com/usage-guide)


## 📊 프로젝트 통계

- **총 코드 라인**: 3,500+ 줄
- **Python 파일**: 9개
- **지원 작물**: 20종 (일부 종 지원)
- **병해충 데이터**: 300+ 종 (일부 지원)
- **RAG 데이터베이스**: 2개 (병해충, 감정 조언)
- **API 통합**: 3개 (NCPMS, OpenAI, Ngrok)
- **개발 기간**: 3일 (2025.11.11 ~ 2025.11.13)

---

## ⚠️ 면책 조항

- 본 시스템의 병해충 진단은 참고용이며, 정확한 진단은 농업 전문가와 상담하시기 바랍니다.
- AI 조언은 일반적인 가이드라인이며, 식물 특성에 따라 다를 수 있습니다.
- NCPMS 데이터는 농촌진흥청에서 제공하며, 저작권은 농촌진흥청에 있습니다.
- OpenAI API 사용 시 비용이 발생할 수 있습니다.
