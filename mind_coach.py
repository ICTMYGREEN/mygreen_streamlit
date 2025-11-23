"""
마음 건강 RAG 시스템 (Mind Coach)
- 사용자의 일기를 분석하여 감정 점수 산출
- RAG를 활용한 개인화된 위로 메시지 제공
- 감정 점수에 따른 맞춤형 조언 (70점 이상/이하 분리)
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma


class MindCoachRAG:
    """마음 건강 RAG 시스템"""
    
    def __init__(self, openai_api_key: str, data_dir: str = "./data", db_dir: str = "./mind_db"):
        """
        Args:
            openai_api_key: OpenAI API 키
            data_dir: PDF 파일이 저장된 디렉토리
            db_dir: ChromaDB가 저장될 디렉토리
        """
        self.openai_api_key = openai_api_key
        self.data_dir = Path(data_dir)
        self.db_dir = Path(db_dir)
        
        # 디렉토리 생성
        self.data_dir.mkdir(exist_ok=True)
        self.db_dir.mkdir(exist_ok=True)
        
        # LLM 및 임베딩 초기화
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=openai_api_key
        )
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=openai_api_key
        )
        
        # Vector DB 초기화 (70점 이상/이하)
        self.db_high = None
        self.db_low = None
        
        # 프롬프트 설정
        self._setup_prompts()
    
    def _setup_prompts(self):
        """프롬프트 템플릿 설정"""
        
        # 감정 분석 프롬프트
        self.emotion_prompt = ChatPromptTemplate.from_template("""
역할: 너는 상처입은 사람들의 마음을 따뜻한 말로 치유하는 어플 MYGREEN의 전문 상담사야.
사용자가 일기를 입력하면 그 일기의 내용을 분석해서 요약 답변을 해줘.

출력 형식 (반드시 JSON 형식으로만 응답):
{{
    "summary": "입력 문장을 요약 (한 문장)",
    "cheer": "상황에 맞는 격려의 말과 오늘 하루를 마무리하는 말 (2-3 문장)",
    "emotion": 감정 점수 (0-100 사이의 정수)
}}

세부 규칙:
- 감정 표현 없이 설명성 문장만 있을 경우 기본적으로 50점 (중립)
- 매우 긍정적인 일기 (예: 기쁜 일, 성취감) → 70~100점
- 중립적이거나 일상적인 일기 (예: 단순 일상 기록) → 40~69점
- 부정적인 감정이 표현된 일기 (예: 슬픔, 분노, 우울) → 0~39점
- 감정 표현의 강도가 클수록 점수를 극단으로 조정 (매우 기쁨 → 90~100, 매우 슬픔 → 0~20)
- "cheer" 항목에는 반드시 오늘 하루를 마무리하는 따뜻한 문장을 포함할 것

사용자 입력:
{user_input}

JSON 형식으로만 응답해줘.
""")
        
        # 식물 메타포 조언 프롬프트
        self.plant_advice_prompt = ChatPromptTemplate.from_template("""
역할: 너는 식물의 성장 과정을 통해 사람의 마음을 치유하는 MYGREEN의 식물 상담사야.

사용자의 감정 상태:
{emotion_summary}

참고할 식물 관련 위로 메시지:
{context}

위 정보를 바탕으로, 식물의 성장 과정이나 특성을 메타포로 사용하여 
사용자에게 따뜻하고 희망적인 조언을 2-3 문장으로 작성해줘.
반드시 식물과 관련된 비유나 이야기를 포함할 것.
""")
        
        # 체인 생성
        self.emotion_chain = self.emotion_prompt | self.llm | StrOutputParser()
        self.plant_advice_chain = self.plant_advice_prompt | self.llm | StrOutputParser()
    
    def initialize_vector_dbs(self, pdf_high: str = None, pdf_low: str = None) -> Tuple[bool, bool]:
        """
        Vector DB 초기화 (70점 이상/이하 분리)
        
        Args:
            pdf_high: 70점 이상용 PDF 파일 경로 (선택)
            pdf_low: 70점 이하용 PDF 파일 경로 (선택)
        
        Returns:
            (db_high 성공 여부, db_low 성공 여부)
        """
        # 기본 경로 설정
        if pdf_high is None:
            pdf_high = "./data/over70.pdf"
        if pdf_low is None:
            pdf_low = "./data/under70.pdf"

        db_high_path = self.db_dir / "db_high"  
        db_low_path = self.db_dir / "db_low"
        
        # 70점 이상 DB
        success_high = False
        try:
            self.db_high = self._load_or_create_db(
                db_path=str(db_high_path),
                doc_path=str(pdf_high),
                label="70점 이상"
            )
            success_high = self.db_high is not None
        except Exception as e:
            print(f"[경고] 70점 이상 DB 초기화 실패: {e}")
        
        # 70점 이하 DB
        success_low = False
        try:
            self.db_low = self._load_or_create_db(
                db_path=str(db_low_path),
                doc_path=str(pdf_low),
                label="70점 이하"
            )
            success_low = self.db_low is not None
        except Exception as e:
            print(f"[경고] 70점 이하 DB 초기화 실패: {e}")
        
        return success_high, success_low
    
    def _load_or_create_db(
        self,
        db_path: str,
        doc_path: str,
        label: str
    ) -> Optional[Chroma]:
        """DB 로드 또는 생성"""
        
        # 이미 DB가 존재하면 로드
        if os.path.exists(db_path) and os.listdir(db_path):
            print(f"[정보] {label} DB 로드 완료: {db_path}")
            return Chroma(
                persist_directory=db_path,
                embedding_function=self.embeddings
            )
        
        # 문서 확인
        if not os.path.exists(doc_path):
            print(f"[경고] PDF 파일을 찾을 수 없습니다: {doc_path}")
            return None
        
        try:
            print(f"[정보] {label} DB 생성 시작...")
            
            # 문서 로드
            loader = PyPDFLoader(doc_path)
            docs = loader.load()
            
            # 문서 분할
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=100
            )
            chunks = splitter.split_documents(docs)
            
            # 임베딩 및 DB 생성
            db = Chroma.from_documents(
                chunks,
                self.embeddings,
                persist_directory=db_path
            )
            
            print(f"[완료] {label} DB 생성 완료 ({len(chunks)}개 청크)")
            return db
        
        except Exception as e:
            print(f"[오류] {label} DB 생성 중 오류 발생: {str(e)}")
            return None
    
    def analyze_emotion(self, diary_text: str) -> Dict[str, any]:
        """
        일기 텍스트 분석 및 감정 점수 산출
        
        Args:
            diary_text: 사용자가 작성한 일기
        
        Returns:
            {
                "summary": str,
                "cheer": str,
                "emotion": int,
                "emotion_label": str,
                "emotion_color": str
            }
        """
        try:
            # LLM을 통한 감정 분석
            response = self.emotion_chain.invoke({"user_input": diary_text})
            
            # JSON 파싱
            emotion_data = json.loads(response)
            emotion_score = emotion_data["emotion"]
            
            # 감정 라벨 및 색상 결정
            if emotion_score >= 70:
                emotion_label = "긍정적"
                emotion_color = ""
            elif emotion_score >= 40:
                emotion_label = "중립적"
                emotion_color = ""
            else:
                emotion_label = "부정적"
                emotion_color = ""
            
            return {
                "summary": emotion_data["summary"],
                "cheer": emotion_data["cheer"],
                "emotion": emotion_score,
                "emotion_label": emotion_label,
                "emotion_color": emotion_color
            }
        
        except json.JSONDecodeError as e:
            print(f"[오류] JSON 파싱 실패: {e}")
            print(f"[응답] {response}")
            raise ValueError("감정 분석 응답이 올바른 JSON 형식이 아닙니다.")
        except Exception as e:
            print(f"[오류] 감정 분석 중 오류 발생: {e}")
            raise
    
    def get_plant_advice(
        self,
        emotion_summary: str,
        emotion_score: int,
        top_k: int = 2
    ) -> Tuple[Optional[str], str]:
        """
        감정 점수에 따른 식물 메타포 조언 생성
        
        Args:
            emotion_summary: 감정 요약 정보
            emotion_score: 감정 점수 (0-100)
            top_k: 검색할 문서 수
        
        Returns:
            (조언 텍스트, DB 라벨)
        """
        # 감정 점수에 따라 적절한 DB 선택
        if emotion_score >= 70:
            selected_db = self.db_high
            db_label = "긍정 메시지"
        else:
            selected_db = self.db_low
            db_label = "위로 메시지"
        
        # DB가 없는 경우 기본 메시지 반환
        if selected_db is None:
            return None, db_label
        
        try:
            # RAG 검색
            retriever = selected_db.as_retriever(search_kwargs={"k": top_k})
            #relevant_docs = retriever.get_relevant_documents(emotion_summary)
            relevant_docs = retriever.invoke(emotion_summary)
            context = "\n".join([doc.page_content for doc in relevant_docs])
            
            # 조언 생성
            advice = self.plant_advice_chain.invoke({
                "emotion_summary": emotion_summary,
                "context": context
            })
            
            return advice, db_label
        
        except Exception as e:
            print(f"[오류] 식물 조언 생성 중 오류 발생: {e}")
            return None, db_label
    
    def get_full_response(self, diary_text: str) -> Dict[str, any]:
        """
        일기 분석 및 전체 응답 생성
        
        Args:
            diary_text: 사용자가 작성한 일기
        
        Returns:
            {
                "summary": str,
                "cheer": str,
                "emotion": int,
                "emotion_label": str,
                "emotion_color": str,
                "plant_advice": str,
                "db_label": str
            }
        """
        # 1. 감정 분석
        emotion_result = self.analyze_emotion(diary_text)
        
        # 2. 식물 조언 생성
        emotion_summary = (
            f"요약: {emotion_result['summary']}\n"
            f"감정 점수: {emotion_result['emotion']}점 ({emotion_result['emotion_label']})"
        )
        
        plant_advice, db_label = self.get_plant_advice(
            emotion_summary=emotion_summary,
            emotion_score=emotion_result["emotion"]
        )
        
        # 기본 메시지 설정
        if plant_advice is None:
            plant_advice = "오늘도 당신의 마음에 귀 기울여주셔서 감사합니다. 식물처럼 천천히, 자신만의 속도로 성장하고 계신 거예요. 🌱"
        
        return {
            **emotion_result,
            "plant_advice": plant_advice,
            "db_label": db_label
        }


def main_example():
    """사용 예시"""
    
    # API 키 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경변수를 설정해주세요.")
    
    # ===== Mind Coach 시스템 초기화 =====
    print("=" * 60)
    print("Mind Coach RAG 시스템 초기화")
    print("=" * 60)
    
    mind_coach = MindCoachRAG(openai_api_key=OPENAI_API_KEY)
    
    # Vector DB 초기화
    success_high, success_low = mind_coach.initialize_vector_dbs()
    print(f"\n[완료] DB 초기화 - 70점 이상: {success_high}, 70점 이하: {success_low}")
    
    # ===== 일기 분석 테스트 =====
    print("\n" + "=" * 60)
    print("일기 분석 테스트")
    print("=" * 60)
    
    # 테스트 일기들
    test_diaries = [
        "오늘 정말 힘든 하루였어요. 회사에서 프로젝트가 잘 안 풀려서 스트레스 받았고, 상사한테 혼났어요. 집에 오니 더 우울해지네요.",
        "오늘은 평범한 하루였어요. 회사 갔다 왔고, 저녁에는 친구랑 카페에서 이야기했어요.",
        "오늘 정말 행복한 날이었어요! 승진 소식을 들었고, 가족들과 저녁을 먹으면서 축하받았어요. 모든 게 완벽했어요!"
    ]
    
    for idx, diary in enumerate(test_diaries, 1):
        print(f"\n[테스트 {idx}] 일기:")
        print(f"  \"{diary}\"\n")
        
        try:
            result = mind_coach.get_full_response(diary)
            
            print(f"📊 감정 분석")
            print(f"  {result['emotion_color']} {result['emotion_label']} (점수: {result['emotion']}점)")
            print(f"\n💭 요약")
            print(f"  {result['summary']}")
            print(f"\n💚 응원 메시지")
            print(f"  {result['cheer']}")
            print(f"\n🌱 식물 조언 ({result['db_label']})")
            print(f"  {result['plant_advice']}")
            print("\n" + "-" * 60)
        
        except Exception as e:
            print(f"[오류] 분석 실패: {e}")


if __name__ == "__main__":
    main_example()