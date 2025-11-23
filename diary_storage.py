"""
마음 일지 저장 시스템
- 식물 별명별로 일지 저장
- CSV 기반 영구 저장
- 날짜 오름차순 관리
"""

import os
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DiaryStorage:
    """일지 저장 관리 클래스"""
    
    def __init__(self, data_dir: str = "./diary_data"):
        """
        Args:
            data_dir: 일지 데이터가 저장될 디렉토리
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.diary_file = self.data_dir / "my_diaries.csv"
        self.df = self._load_or_create_dataframe()
    
    def _load_or_create_dataframe(self) -> pd.DataFrame:
        """데이터프레임 로드 또는 생성"""
        if self.diary_file.exists():
            try:
                df = pd.read_csv(self.diary_file, encoding='utf-8-sig')
                df['날짜'] = pd.to_datetime(df['날짜'])
                print(f"[정보] 기존 일지 로드: {len(df)}개")
                return df
            except Exception as e:
                print(f"[경고] 데이터 로드 실패, 새로 생성: {e}")
        
        # 새 데이터프레임
        df = pd.DataFrame(columns=[
            '날짜',        # 작성 날짜시간
            '식물이름',    # 식물 별명
            '일지내용',    # 사용자 작성 일기
            '요약',        # AI 요약
            '감정점수',    # 0-100
            '감정라벨',    # 긍정적/중립적/부정적
            '응원메시지',  # AI 응원
            '식물조언',    # 식물 메타포 조언
        ])
        print("[정보] 새 일지 데이터프레임 생성")
        return df
    
    def save_diary(
        self,
        plant_name: str,
        diary_content: str,
        analysis_result: Dict
    ) -> bool:
        """
        일지 저장
        
        Args:
            plant_name: 식물 별명
            diary_content: 사용자가 작성한 일기
            analysis_result: mind_coach.get_full_response() 결과
        
        Returns:
            성공 여부
        """
        try:
            # 새 항목 데이터
            new_data = {
                '날짜': datetime.now(),
                '식물이름': plant_name,
                '일지내용': diary_content,
                '요약': analysis_result.get('summary', ''),
                '감정점수': analysis_result.get('emotion', 50),
                '감정라벨': analysis_result.get('emotion_label', '중립적'),
                '응원메시지': analysis_result.get('cheer', ''),
                '식물조언': analysis_result.get('plant_advice', ''),
            }
            
            # 빈 데이터프레임인 경우
            if len(self.df) == 0:
                self.df = pd.DataFrame([new_data])
            else:
                # 기존 데이터가 있는 경우
                new_entry = pd.DataFrame([new_data])
                self.df = pd.concat([self.df, new_entry], ignore_index=True)
            
            # CSV 저장
            self.df.to_csv(self.diary_file, index=False, encoding='utf-8-sig')
            
            print(f"[완료] 일지 저장: {plant_name}")
            return True
        
        except Exception as e:
            print(f"[오류] 일지 저장 실패: {e}")
            return False
    
    def reload_data(self):
        """CSV 파일에서 데이터 다시 로드"""
        self.df = self._load_or_create_dataframe()
    
    def get_plant_diaries(
        self,
        plant_name: str,
        sort_ascending: bool = True
    ) -> pd.DataFrame:
        """
        특정 식물의 일지 조회
        
        Args:
            plant_name: 식물 별명
            sort_ascending: True=오름차순(오래된것부터), False=내림차순
        
        Returns:
            필터링된 데이터프레임
        """
        # 매번 최신 데이터 로드
        self.reload_data()
        
        filtered = self.df[self.df['식물이름'] == plant_name].copy()
        filtered = filtered.sort_values('날짜', ascending=sort_ascending)
        return filtered.reset_index(drop=True)
    
    def get_all_plants(self) -> List[str]:
        """모든 식물 이름 목록"""
        # 매번 최신 데이터 로드
        self.reload_data()
        
        return sorted(self.df['식물이름'].unique().tolist())
    
    def get_statistics(self, plant_name: str) -> Dict:
        """
        식물별 통계
        
        Args:
            plant_name: 식물 별명
        
        Returns:
            통계 딕셔너리
        """
        # 최신 데이터로 조회
        df = self.get_plant_diaries(plant_name)
        
        if len(df) == 0:
            return {
                "총_일지_수": 0,
                "평균_감정점수": 0,
                "긍정적_비율": 0,
                "중립적_비율": 0,
                "부정적_비율": 0,
            }
        
        label_counts = df['감정라벨'].value_counts()
        total = len(df)
        
        return {
            "총_일지_수": total,
            "평균_감정점수": round(df['감정점수'].mean(), 1),
            "최고_감정점수": int(df['감정점수'].max()),
            "최저_감정점수": int(df['감정점수'].min()),
            "긍정적_비율": round(label_counts.get('긍정적', 0) / total * 100, 1),
            "중립적_비율": round(label_counts.get('중립적', 0) / total * 100, 1),
            "부정적_비율": round(label_counts.get('부정적', 0) / total * 100, 1),
            "최근_7일_평균": round(df.tail(7)['감정점수'].mean(), 1) if len(df) >= 7 else round(df['감정점수'].mean(), 1),
            "시작_날짜": df.iloc[0]['날짜'].strftime('%Y-%m-%d'),
            "마지막_날짜": df.iloc[-1]['날짜'].strftime('%Y-%m-%d'),
        }
    
    def delete_diary(self, plant_name: str, index: int) -> bool:
        """
        특정 일지 삭제
        
        Args:
            plant_name: 식물 별명
            index: 삭제할 일지 인덱스
        
        Returns:
            성공 여부
        """
        try:
            plant_df = self.get_plant_diaries(plant_name)
            
            if index < 0 or index >= len(plant_df):
                print("[오류] 유효하지 않은 인덱스")
                return False
            
            date_to_delete = plant_df.iloc[index]['날짜']
            content_to_delete = plant_df.iloc[index]['일지내용']
            
            mask = (self.df['식물이름'] == plant_name) & \
                   (self.df['날짜'] == date_to_delete) & \
                   (self.df['일지내용'] == content_to_delete)
            
            self.df = self.df[~mask]
            self.df.to_csv(self.diary_file, index=False, encoding='utf-8-sig')
            
            print("[완료] 일지 삭제")
            return True
        
        except Exception as e:
            print(f"[오류] 삭제 실패: {e}")
            return False


# 테스트
if __name__ == "__main__":
    # 저장소 초기화 테스트
    storage = DiaryStorage()
    
    # 저장된 식물 목록 확인
    plants = storage.get_all_plants()
    print(f"저장된 식물: {plants}")
    
    # 각 식물별 일지 수 확인
    for plant in plants:
        diaries = storage.get_plant_diaries(plant)
        print(f"{plant}: {len(diaries)}개 일지")