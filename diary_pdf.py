"""
마음 일지 PDF 책자 생성기
- 식물별 일지를 아름다운 책자 형태로 출력
- 한글 지원
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, 
    Table, TableStyle, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class DiaryPDFMaker:
    """일지 PDF 책자 생성 클래스"""
    
    def __init__(self, output_dir: str = "./diary_pdfs"):
        """
        Args:
            output_dir: PDF 파일 저장 디렉토리
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self._register_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_styles()
    
    def _register_fonts(self):
        """한글 폰트 등록"""
        try:
            font_paths = [
                "C:/Windows/Fonts/malgun.ttf",
                "C:/Windows/Fonts/batang.ttf",
                "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/System/Library/Fonts/AppleGothic.ttf",
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('Korean', font_path))
                    print(f"[정보] 폰트 등록: {font_path}")
                    self.has_korean = True
                    return
            
            print("[경고] 한글 폰트 없음 - 기본 폰트 사용")
            self.has_korean = False
        
        except Exception as e:
            print(f"[경고] 폰트 등록 실패: {e}")
            self.has_korean = False
    
    def _setup_styles(self):
        """스타일 설정"""
        font = 'Korean' if self.has_korean else 'Helvetica'
        
        # 제목
        self.styles.add(ParagraphStyle(
            name='BookTitle',
            parent=self.styles['Title'],
            fontName=font,
            fontSize=28,
            textColor=colors.HexColor('#2f6f3e'),
            alignment=TA_CENTER,
            spaceAfter=30,
            leading=35
        ))
        
        # 부제목
        self.styles.add(ParagraphStyle(
            name='BookSubtitle',
            parent=self.styles['Heading1'],
            fontName=font,
            fontSize=18,
            textColor=colors.HexColor('#4a7c59'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        
        # 섹션 제목
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading1'],
            fontName=font,
            fontSize=16,
            textColor=colors.HexColor('#2f6f3e'),
            spaceAfter=15,
            spaceBefore=15
        ))
        
        # 본문
        self.styles.add(ParagraphStyle(
            name='BookBody',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=11,
            leading=20,
            spaceAfter=10
        ))
        
        # 날짜
        self.styles.add(ParagraphStyle(
            name='DiaryDate',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=10,
            textColor=colors.grey,
            alignment=TA_RIGHT,
            spaceAfter=8
        ))
        
        # 작은 텍스트
        self.styles.add(ParagraphStyle(
            name='SmallText',
            parent=self.styles['Normal'],
            fontName=font,
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))
    
    def create_diary_book(
        self,
        df: pd.DataFrame,
        plant_name: str,
        statistics: Optional[dict] = None
    ) -> str:
        """
        일지 책자 PDF 생성
        
        Args:
            df: 일지 데이터프레임 (날짜 오름차순)
            plant_name: 식물 별명
            statistics: 통계 정보
        
        Returns:
            생성된 PDF 파일 경로
        """
        if len(df) == 0:
            raise ValueError("출력할 일지가 없습니다.")
        
        # 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{plant_name}_일지_{timestamp}.pdf"
        filepath = self.output_dir / filename
        
        # PDF 문서
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"{plant_name}의 마음 일지"
        )
        
        story = []
        
        # 1. 표지
        story.extend(self._create_cover(plant_name, len(df), df))
        story.append(PageBreak())
        
        # 2. 통계 페이지
        if statistics:
            story.extend(self._create_stats(statistics, plant_name))
            story.append(PageBreak())
        
        # 3. 일지 내용
        for idx, row in df.iterrows():
            story.extend(self._create_entry(row, idx + 1))
            
            # 마지막 항목 아니면 구분선
            if idx < len(df) - 1:
                story.append(Spacer(1, 0.4*inch))
                story.append(self._divider())
                story.append(Spacer(1, 0.4*inch))
        
        # PDF 빌드
        doc.build(story)
        print(f"[완료] PDF 생성: {filepath}")
        return str(filepath)
    
    def _create_cover(self, plant_name: str, total: int, df: pd.DataFrame) -> list:
        """표지 페이지"""
        elements = []
        
        elements.append(Spacer(1, 2*inch))
        
        # 메인 제목
        title = Paragraph("🌱<br/>나의 마음 일지", self.styles['BookTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # 식물 이름
        subtitle = Paragraph(f"<b>{plant_name}</b>와 함께한 성장 기록", self.styles['BookSubtitle'])
        elements.append(subtitle)
        elements.append(Spacer(1, inch))
        
        # 정보 테이블
        start_date = df.iloc[0]['날짜'].strftime('%Y년 %m월 %d일')
        end_date = df.iloc[-1]['날짜'].strftime('%Y년 %m월 %d일')
        created_date = datetime.now().strftime('%Y년 %m월 %d일')
        
        info_data = [
            ['식물 이름', plant_name],
            ['총 일지 수', f"{total}개"],
            ['시작일', start_date],
            ['마지막 기록', end_date],
            ['책자 생성일', created_date],
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 9*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean' if self.has_korean else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2f6f3e')),
            ('FONTNAME', (0, 0), (0, -1), 'Korean' if self.has_korean else 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 1.5*inch))
        
        # 하단 텍스트
        footer = Paragraph(
            "이 책자는 당신의 감정과 성장을 기록한 소중한 기억입니다.",
            self.styles['SmallText']
        )
        elements.append(footer)
        
        return elements
    
    def _create_stats(self, stats: dict, plant_name: str) -> list:
        """통계 페이지"""
        elements = []
        
        # 제목
        title = Paragraph(f"📊 {plant_name}의 감정 여정", self.styles['SectionTitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # 핵심 지표
        key_data = [
            ['총 기록 수', f"{stats['총_일지_수']}개"],
            ['평균 감정 점수', f"{stats['평균_감정점수']}점"],
            ['감정 범위', f"{stats['최저_감정점수']}점 ~ {stats['최고_감정점수']}점"],
            ['최근 7일 평균', f"{stats['최근_7일_평균']}점"],
        ]
        
        key_table = Table(key_data, colWidths=[5*cm, 6*cm])
        key_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean' if self.has_korean else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 13),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2f6f3e')),
            ('FONTNAME', (0, 0), (0, -1), 'Korean' if self.has_korean else 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e0e0e0')),
        ]))
        elements.append(key_table)
        elements.append(Spacer(1, 0.4*inch))
        
        # 감정 분포
        dist_title = Paragraph("감정 분포", self.styles['BookBody'])
        elements.append(dist_title)
        elements.append(Spacer(1, 0.1*inch))
        
        dist_data = [
            ['긍정적', f"{stats['긍정적_비율']}%"],
            ['중립적', f"{stats['중립적_비율']}%"],
            ['부정적', f"{stats['부정적_비율']}%"],
        ]
        
        dist_table = Table(dist_data, colWidths=[5*cm, 6*cm])
        dist_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Korean' if self.has_korean else 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(dist_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # 해석
        avg = stats['평균_감정점수']
        if avg >= 70:
            msg = f"{plant_name}는 건강하게 성장하고 있습니다! 긍정적인 에너지가 가득한 시기입니다. 🌟"
        elif avg >= 40:
            msg = f"{plant_name}는 안정적으로 뿌리를 내리고 있습니다. 작은 변화들이 쌓여 큰 성장을 만듭니다. 🌱"
        else:
            msg = f"{plant_name}가 힘든 시기를 보내고 있지만, 기록하는 용기가 있습니다. 천천히 회복할 거예요. 💚"
        
        interp = Paragraph(msg, self.styles['BookBody'])
        elements.append(interp)
        
        return elements
    
    def _create_entry(self, row: pd.Series, num: int) -> list:
        """개별 일지 항목"""
        elements = []
        
        # 헤더: 번호 + 날짜
        date_str = pd.to_datetime(row['날짜']).strftime('%Y년 %m월 %d일 %H:%M')
        header_text = f"<b>일지 #{num}</b> · {date_str}"
        header = Paragraph(header_text, self.styles['DiaryDate'])
        elements.append(header)
        
        # 감정 배지
        score = int(row['감정점수'])
        label = row['감정라벨']
        
        if score >= 70:
            emoji = ''
        elif score >= 40:
            emoji = ''
        else:
            emoji = ''
        
        emotion_text = f"{emoji} <b>{label}</b> · {score}점"
        emotion = Paragraph(emotion_text, self.styles['BookBody'])
        elements.append(emotion)
        elements.append(Spacer(1, 0.15*inch))
        
        # 일지 내용 박스
        content = row['일지내용'].replace('\n', '<br/>')
        content_para = Paragraph(f"<i>{content}</i>", self.styles['BookBody'])
        
        content_box = Table([[content_para]], colWidths=[15*cm])
        content_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('PADDING', (0, 0), (-1, -1), 15),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(content_box)
        elements.append(Spacer(1, 0.2*inch))
        
        # AI 분석
        sections = [
            ('💭 요약', row['요약']),
            ('💚 응원', row['응원메시지']),
            ('🌱 조언', row['식물조언']),
        ]
        
        for label, text in sections:
            label_para = Paragraph(f"<b>{label}</b>", self.styles['BookBody'])
            text_para = Paragraph(text, self.styles['BookBody'])
            elements.append(label_para)
            elements.append(text_para)
            elements.append(Spacer(1, 0.12*inch))
        
        return elements
    
    def _divider(self):
        """구분선"""
        line = Table([['']], colWidths=[15*cm], rowHeights=[1])
        line.setStyle(TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ]))
        return line


# 테스트
if __name__ == "__main__":
    from diary_storage import DiaryStorage
    
    storage = DiaryStorage()
    plants = storage.get_all_plants()
    
    if len(plants) > 0:
        plant = plants[0]
        df = storage.get_plant_diaries(plant)
        stats = storage.get_statistics(plant)
        
        pdf_maker = DiaryPDFMaker()
        pdf_path = pdf_maker.create_diary_book(df, plant, stats)
        print(f"PDF: {pdf_path}")
    else:
        print("일지 없음")