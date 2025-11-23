"""
식물 병해충 RAG 시스템
- 작물별 병해충 데이터 수집 (NCPMS API)
- ChromaDB를 활용한 벡터 저장 및 검색
- 문제 상황 텍스트 전처리 및 유사 병해충 추천 (Top-K=3)
"""

import os
import re
import requests
from io import BytesIO
from PIL import Image
from typing import List, Dict, Tuple
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI


class PlantDiseaseCollector:
    """NCPMS API를 통한 병해충 데이터 수집"""
    
    def __init__(self, api_key: str, base_url: str = "http://ncpms.rda.go.kr/npmsAPI/service"):
        self.api_key = api_key
        self.base_url = base_url
        self.image_dir = Path("./crop_images")
        self.image_dir.mkdir(exist_ok=True)
    
    @staticmethod
    def cleaning_str(text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        clean_text = text.replace("～", "~").replace("㎜", "mm")
        clean_text = clean_text.replace("<br>", " ").replace("<br/>", " ")
        clean_text = clean_text.replace("\n", " ").replace("\r", " ")
        clean_text = re.sub(r'\s+', ' ', clean_text)  # 연속 공백 제거
        return clean_text.strip()
    
    def get_crop_diseases(self, crop_name: str) -> List[Dict[str, str]]:
        """특정 작물의 병해충 목록 가져오기"""
        params = {
            "apiKey": self.api_key,
            "serviceCode": "SVC01",
            "serviceType": "AA003",
            "cropName": crop_name
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "service" in data and "list" in data["service"]:
                return data["service"]["list"]
            return []
        except Exception as e:
            print(f"[오류] 작물 정보 조회 실패: {e}")
            return []
    
    def get_disease_detail(self, sick_key: str) -> Dict[str, str]:
        """특정 병해충의 상세 정보 가져오기"""
        params = {
            "apiKey": self.api_key,
            "serviceCode": "SVC05",
            "sickKey": sick_key
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if "service" in data:
                sick_info = data["service"]
                return {
                    "병명": self.cleaning_str(sick_info.get("sickNameKor", "")),
                    "발생생태": self.cleaning_str(sick_info.get("developmentCondition", "")),
                    "병 증상": self.cleaning_str(sick_info.get("symptoms", "")),
                    "방제방법": self.cleaning_str(sick_info.get("preventionMethod", ""))
                }
            return {}
        except Exception as e:
            print(f"[오류] 병해충 상세 정보 조회 실패 ({sick_key}): {e}")
            return {}
    
    def save_disease_image(self, crop_name: str, disease_name: str, img_url: str) -> str:
        """병해충 이미지 저장 및 경로 반환"""
        # noImg 체크
        if img_url == "http://ncpms.rda.go.kr/images/common/noImg.gif":
            print(f"    [이미지] {disease_name}: 기본 이미지(noImg) - 스킵")
            return None
        
        # 빈 URL 체크
        if not img_url or img_url.strip() == "":
            print(f"    [이미지] {disease_name}: 이미지 URL 없음 - 스킵")
            return None
        
        try:
            print(f"    [이미지] {disease_name}: 다운로드 시작 - {img_url}")
            response = requests.get(img_url, timeout=20)
            response.raise_for_status()
            
            img = Image.open(BytesIO(response.content))
            # 파일명 정규화 (특수문자 제거)
            safe_disease_name = re.sub(r'[^\w\s-]', '', disease_name).strip()
            safe_disease_name = re.sub(r'[-\s]+', '_', safe_disease_name)
            filename = f"{crop_name}_{safe_disease_name}.png"
            filepath = self.image_dir / filename
            img.save(filepath)
            print(f"    [이미지] {disease_name}: 저장 완료 - {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"    [오류] 이미지 저장 실패 ({disease_name}): {e}")
            print(f"    [오류] URL: {img_url}")
            return None
    
    def collect_all_data(self, crop_name: str) -> List[Dict[str, str]]:
        """작물의 모든 병해충 데이터 수집"""
        print(f"[정보] '{crop_name}' 병해충 데이터 수집 시작...")
        
        # 1. 병해충 목록 가져오기
        disease_list = self.get_crop_diseases(crop_name)
        if not disease_list:
            print(f"[경고] '{crop_name}'에 대한 병해충 정보가 없습니다.")
            return []
        
        
        print(f"[완료] {len(disease_list)}개의 병해충 발견")
        print(f"[디버그] API에서 받은 병해충 목록:")
        for idx, disease in enumerate(disease_list, 1):
            disease_name = disease.get("sickNameKor", f"병{idx}")
            print(f"  - {disease_name}")
        
        # 2. 각 병해충의 상세 정보 가져오기
        all_diseases = []
        for idx, disease in enumerate(disease_list, 1):
            sick_key = disease.get("sickKey")
            disease_name = disease.get("sickNameKor", f"병{idx}")
            
            print(f"  [{idx}/{len(disease_list)}] {disease_name} 처리 중...")
            
            # 상세 정보
            detail = self.get_disease_detail(sick_key)
            if detail:
                detail["작물명"] = crop_name
                detail["sickKey"] = sick_key
                
                # 이미지 저장 및 경로 추가
                if "thumbImg" in disease:
                    img_path = self.save_disease_image(crop_name, disease_name, disease["thumbImg"])
                    detail["이미지경로"] = img_path
                else:
                    detail["이미지경로"] = None
                
                all_diseases.append(detail)
        
        print(f"[완료] 총 {len(all_diseases)}개의 병해충 데이터 수집 완료")
        print(f"[디버그] 저장된 병해충 목록:")
        for idx, disease in enumerate(all_diseases, 1):
            print(f"  - {disease.get('병명', '알 수 없음')}")
        print()
        return all_diseases

        return all_diseases


class TextPreprocessor:
    """문제 상황 텍스트 전처리"""
    
    @staticmethod
    def preprocess(text: str) -> str:
        """텍스트 전처리 파이프라인"""
        if not text:
            return ""
        
        # 1. 소문자 변환 (선택적)
        # text = text.lower()
        
        # 2. 특수문자 정리
        text = re.sub(r'[^\w\s가-힣]', ' ', text)
        
        # 3. 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 4. 불용어 제거 (선택적)
        stopwords = {'입니다', '있습니다', '했습니다', '됩니다', '것', '수', '등'}
        words = text.split()
        words = [w for w in words if w not in stopwords]
        
        # 5. 키워드 강조 (증상 관련 단어 추출)
        symptom_keywords = ['잎', '줄기', '뿌리', '꽃', '열매', '시들', '썩', '반점', 
                           '갈변', '황화', '위축', '곰팡이', '벌레', '구멍']
        important_words = [w for w in words if any(kw in w for kw in symptom_keywords)]
        
        # 6. 중요 단어를 앞쪽에 배치
        other_words = [w for w in words if w not in important_words]
        processed_words = important_words + other_words
        
        return ' '.join(processed_words).strip()


class PlantDiseaseRAG:
    """ChromaDB 기반 병해충 RAG 시스템"""
    
    # 검증용 작물 한글-코드 매핑
    CROP_NAME_MAP = {
        #'감자': 'FC050501',
        #'논벼' :'FC010101',
        #'토마토': 'VC010803'
        '국화' : 'FL022402',
        '작약' : 'FL022425',    
        '카네이션' : 'FL022427',    
        '장미' : 'FL082028',    
        '과꽃' : 'FL012105',    
        '봉숭아(봉선화)' : 'FL012131',    }
    
    def __init__(self, openai_api_key: str, chroma_base_dir: str = "./chroma_db"):
        self.openai_api_key = openai_api_key
        self.chroma_base_dir = Path(chroma_base_dir)
        self.chroma_base_dir.mkdir(exist_ok=True)
        self.embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        self.client = OpenAI(api_key=openai_api_key)
        self.preprocessor = TextPreprocessor()
    
    @classmethod
    def get_supported_crops(cls) -> List[str]:
        """지원하는 작물 목록 반환 (한글)"""
        return list(cls.CROP_NAME_MAP.keys())
    
    @classmethod
    def is_supported_crop(cls, crop_name: str) -> bool:
        """지원하는 작물인지 확인"""
        return crop_name in cls.CROP_NAME_MAP
    
    def _get_c_code_name(self, crop_name: str) -> str:
        """한글 작물명을 영문으로 변환"""
        if crop_name in self.CROP_NAME_MAP:
            return self.CROP_NAME_MAP[crop_name]
        raise ValueError(f"'{crop_name}'는 지원하지 않는 작물입니다. 지원 작물: {', '.join(self.CROP_NAME_MAP.keys())}")
    
    def _get_collection_name(self, crop_name: str) -> str:
        """작물명으로부터 컬렉션명 생성 (영문명 사용)"""
        # 한글이면 코드로 변환
        if crop_name in self.CROP_NAME_MAP:
            c_code_name = self.CROP_NAME_MAP[crop_name]
        else:
            # 코드면 그대로 사용 (이미 코드로 입력된 경우)
            c_code_name = crop_name.lower()
        
        collection_name = f"crop_{c_code_name}"
        # ChromaDB 규칙 검증: 영문/숫자/._- 만 허용
        collection_name = re.sub(r'[^\w._-]', '_', collection_name).lower()
        return collection_name
    
    def _get_chroma_dir(self, crop_name: str) -> Path:
        """작물별 ChromaDB 디렉토리 경로"""
        collection_name = self._get_collection_name(crop_name)
        return self.chroma_base_dir / collection_name
    
    def create_crop_index(self, crop_name: str, diseases: List[Dict[str, str]]) -> Chroma:
        """작물별 병해충 인덱스 생성"""
        # 지원하는 작물인지 확인
        if not self.is_supported_crop(crop_name):
            raise ValueError(
                f"'{crop_name}'는 지원하지 않는 작물입니다.\n"
                f"지원 작물: {', '.join(self.get_supported_crops())}"
            )
        
        c_code_name = self._get_c_code_name(crop_name)
        print(f"[인덱스] '{crop_name}({c_code_name})' ChromaDB 인덱스 생성 중...")
        
        # Document 생성
        documents = []
        for disease in diseases:
            # 병해충 정보를 하나의 문서로 구성
            content = (
                f"병명: {disease.get('병명', '')}\n\n"
                f"발생생태:\n{disease.get('발생생태', '정보 없음')}\n\n"
                f"병 증상:\n{disease.get('병 증상', '정보 없음')}\n\n"
                f"방제방법:\n{disease.get('방제방법', '정보 없음')}"
            )
            
            # 메타데이터에 구조화된 정보 포함
            metadata = {
                "disease_name": disease.get('병명', ''),
                "crop_name": crop_name,  # 한글 이름 유지
                "crop_code": c_code_name,
                "has_ecology": bool(disease.get('발생생태')),
                "has_symptoms": bool(disease.get('병 증상')),
                "has_prevention": bool(disease.get('방제방법')),
                "image_path": disease.get('이미지경로', '')  # 이미지 경로 추가
            }
            
            documents.append(Document(page_content=content, metadata=metadata))
        
        # ChromaDB 생성 (작물별 디렉토리에 저장)
        chroma_dir = self._get_chroma_dir(crop_name)
        collection_name = self._get_collection_name(crop_name)
        
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=collection_name
        )
        
        print(f"[완료] '{crop_name}' 인덱스 생성 완료 ({len(documents)}개 문서)")
        print(f"   컬렉션명: {collection_name}")
        return vectorstore
    
    def load_crop_index(self, crop_name: str) -> Chroma:
        """기존 작물 인덱스 로드"""
        chroma_dir = self._get_chroma_dir(crop_name)
        collection_name = self._get_collection_name(crop_name)
        
        if not chroma_dir.exists():
            raise FileNotFoundError(f"'{crop_name}'의 인덱스가 존재하지 않습니다.")
        
        vectorstore = Chroma(
            persist_directory=str(chroma_dir),
            embedding_function=self.embeddings,
            collection_name=collection_name
        )
        
        return vectorstore
    
    def search_similar_diseases(
        self, 
        crop_name: str, 
        problem_text: str, 
        top_k: int = 3
    ) -> List[Tuple[str, float, str, str]]:
        """
        문제 상황으로부터 유사 병해충 검색
        
        Returns:
            List of (병명, 유사도 점수, 원본 문서 내용, 이미지 경로)
        """
        # 1. 텍스트 전처리
        processed_query = self.preprocessor.preprocess(problem_text)
        print(f"[검색] 원본 쿼리: {problem_text}")
        print(f"[검색] 전처리 쿼리: {processed_query}")
        
        # 2. 벡터 스토어 로드
        try:
            vectorstore = self.load_crop_index(crop_name)
        except FileNotFoundError:
            print(f"[경고] '{crop_name}'의 인덱스를 찾을 수 없습니다.")
            return []
        
        # 3. 유사도 검색 (Top-K=3 고정) - 작물명 필터 적용
        results = vectorstore.similarity_search_with_score(
            processed_query,
            k=top_k,
            filter={"crop_name": crop_name}  # 해당 작물만 검색
        )
        
        # 4. 결과 정리 및 이중 검증
        similar_diseases = []
        for doc, score in results:
            # 메타데이터에서 작물명 확인
            doc_crop_name = doc.metadata.get("crop_name", "")
            
            # 작물명이 일치하는 경우만 포함
            if doc_crop_name == crop_name:
                disease_name = doc.metadata.get("disease_name", "알 수 없음")
                image_path = doc.metadata.get("image_path", "")
                similar_diseases.append((disease_name, score, doc.page_content, image_path))
        
        print(f"[검색] '{crop_name}'에서 {len(similar_diseases)}개 결과 발견")
        return similar_diseases
    
    
    def get_disease_detail_answer(
        self, 
        crop_name: str, 
        disease_name: str
    ) -> str:
        """선택된 병해충의 상세 정보 RAG 답변 생성"""
        
        # 1. 벡터 스토어에서 해당 병해충 정보 검색
        vectorstore = self.load_crop_index(crop_name)
        
        # 필터 없이 병명으로 검색하고 수동 필터링
        results = vectorstore.similarity_search(f"병명: {disease_name}", k=10)
        
        # 병명이 정확히 일치하는 것만 선택
        filtered_results = []
        for r in results:
            if r.metadata.get("disease_name") == disease_name and r.metadata.get("crop_name") == crop_name:
                filtered_results.append(r)
        
        if not filtered_results:
            return f"'{disease_name}' 정보를 찾을 수 없습니다. 작물이 올바른지 확인해주세요."
        
        context = filtered_results[0].page_content
        
        print(f"[상세정보] '{disease_name}' 컨텍스트 로드 완료")
        print(f"[컨텍스트 미리보기] {context[:200]}...")
        
        # 2. LLM을 통한 답변 생성
        system_prompt = """당신은 친절하고 전문적인 농업 병해 상담 어시스턴트입니다.
주어진 컨텍스트 내 정보만을 사용하여 한국어로 간결하고 이해하기 쉽게 답변하세요.

답변은 아래 형식을 따릅니다:
① [발생 원인] — 해당 병이 생기는 주요 원인이나 조건을 설명합니다.
② [주요 증상] — 농작물에서 관찰되는 대표적인 증상을 요약합니다.
③ [방제 방법] — 예방 및 대응에 도움이 되는 구체적인 방제 또는 관리 방법을 제시합니다.

가능하면 부드럽고 조언하는 말투로 작성하세요 (예: '~할 수 있습니다', '~하는 것이 좋습니다').
컨텍스트에 정보가 없거나 불확실한 경우에는 반드시 '데이터 없음'이라고 표시하세요."""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": f"[컨텍스트]\n{context}\n\n질문: '{disease_name}'에 대해 발생 원인, 주요 증상, 방제 방법을 항목별로 간결하게 정리해줘."
            }
        ]
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )
        
        return response.choices[0].message.content


def main_example():
    """사용 예시"""
    
    # API 키 설정
    NCPMS_API_KEY = os.getenv("NCPMS_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY 환경변수를 설정해주세요.")
    
    # ===== RAG 시스템 초기화 =====
    rag_system = PlantDiseaseRAG(openai_api_key=OPENAI_API_KEY)
    
    print("=" * 60)
    print("지원 작물 목록")
    print("=" * 60)
    print(", ".join(rag_system.get_supported_crops()))
    
    # ===== 1단계: 작물 등록 및 데이터 수집 =====
    print("\n" + "=" * 60)
    print("1단계: 작물 등록 및 병해충 데이터 수집")
    print("=" * 60)
    
    collector = PlantDiseaseCollector(api_key=NCPMS_API_KEY)
    crop_name = "토마토"  # 사용자가 입력한 작물명 (한글)
    
    # 지원 작물 확인
    if not rag_system.is_supported_crop(crop_name):
        print(f"[오류] '{crop_name}'는 지원하지 않는 작물입니다.")
        print(f"   지원 작물: {', '.join(rag_system.get_supported_crops())}")
        return
    
    diseases = collector.collect_all_data(crop_name)
    
    if not diseases:
        print("병해충 데이터를 수집할 수 없습니다.")
        return
    
    # ===== 2단계: ChromaDB 인덱스 생성 =====
    print("\n" + "=" * 60)
    print("2단계: ChromaDB 인덱스 생성 (RAG 학습)")
    print("=" * 60)
    
    rag_system.create_crop_index(crop_name, diseases)
    
    # ===== 3단계: 문제 상황 입력 및 유사 병해충 검색 =====
    print("\n" + "=" * 60)
    print("3단계: 문제 상황 진단")
    print("=" * 60)
    
    problem_text = "잎에 갈색 반점이 생기고 점점 시들어요"  # 사용자 입력
    
    similar_diseases = rag_system.search_similar_diseases(
        crop_name=crop_name,
        problem_text=problem_text,
        top_k=3
    )
    
    print(f"\n유사 병해충 Top-3:")
    for idx, (disease_name, score, _) in enumerate(similar_diseases, 1):
        print(f"  {idx}. {disease_name} (유사도: {score:.4f})")
    
    # ===== 4단계: 사용자가 병해충 선택 및 상세 정보 제공 =====
    print("\n" + "=" * 60)
    print("4단계: 선택된 병해충 상세 정보")
    print("=" * 60)
    
    if similar_diseases:
        selected_disease = similar_diseases[0][0]  # 사용자가 선택 (여기서는 1번)
        print(f"\n[완료] 선택된 병: {selected_disease}\n")
        
        detail_answer = rag_system.get_disease_detail_answer(crop_name, selected_disease)
        print(detail_answer)


if __name__ == "__main__":
    main_example()