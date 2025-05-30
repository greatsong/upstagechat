import streamlit as st
import requests
import json
import pandas as pd
from io import BytesIO
import base64
import re

# 페이지 구성 및 API 설정
st.set_page_config(page_title="📄 Upstage Multi-Tool", layout="wide")
api_key = st.secrets["upstage_api_key"]
base_url = "https://api.upstage.ai/v1"

# 사이드바 네비게이션
st.sidebar.title("🔧 기능 선택")
page = st.sidebar.radio("페이지 선택", ["문서 파싱", "OCR", "정보 추출"])

# 공통 헤더
headers = {"Authorization": f"Bearer {api_key}"}

# HTML을 마크다운으로 변환하는 함수
def html_to_markdown(html_content):
    """HTML을 마크다운으로 변환"""
    # 제목 변환
    html_content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', html_content)
    html_content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', html_content)
    html_content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', html_content)
    
    # 줄바꿈
    html_content = html_content.replace('<br>', '\n').replace('<br/>', '\n')
    
    # 단락
    html_content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', html_content)
    
    # 볼드
    html_content = re.sub(r'<strong>(.*?)</strong>', r'**\1**', html_content)
    html_content = re.sub(r'<b>(.*?)</b>', r'**\1**', html_content)
    
    # 이탤릭
    html_content = re.sub(r'<em>(.*?)</em>', r'*\1*', html_content)
    html_content = re.sub(r'<i>(.*?)</i>', r'*\1*', html_content)
    
    # 나머지 HTML 태그 제거
    html_content = re.sub(r'<[^>]+>', '', html_content)
    
    return html_content.strip()

# 표 추출 함수
def extract_tables_from_html(html_content):
    """HTML에서 표 추출"""
    tables = []
    table_pattern = r'<table[^>]*>(.*?)</table>'
    table_matches = re.findall(table_pattern, html_content, re.DOTALL)
    
    for table_html in table_matches:
        rows = []
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        row_matches = re.findall(row_pattern, table_html, re.DOTALL)
        
        for row_html in row_matches:
            cells = []
            cell_pattern = r'<t[hd][^>]*>(.*?)</t[hd]>'
            cell_matches = re.findall(cell_pattern, row_html, re.DOTALL)
            
            for cell in cell_matches:
                # HTML 태그 제거
                clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                cells.append(clean_cell)
            
            if cells:
                rows.append(cells)
        
        if rows:
            tables.append(rows)
    
    return tables

# ─── 문서 파싱 페이지 ───────────────────────────────────────────────────────────
if page == "문서 파싱":
    st.header("📄 문서 파싱 (Document Parsing)")
    uploaded = st.file_uploader("PDF/이미지 파일 업로드", type=["pdf","png","jpg","jpeg"])
    
    if uploaded:
        st.write(f"파일명: {uploaded.name}")
        
        # 옵션 설정
        col1, col2 = st.columns(2)
        with col1:
            encode_option = st.selectbox(
                "Base64 인코딩 옵션",
                ["없음", "표만", "텍스트만", "텍스트와 표"]
            )
        with col2:
            output_format = st.multiselect(
                "출력 형식",
                ["html", "text", "markdown"],
                default=["html", "markdown"]
            )
        
        data = {
            "ocr": "auto",
            "model": "document-parse",
            "coordinates": "true"
        }
        
        # output_formats 설정
        if output_format:
            data["output_formats"] = str(output_format).replace("'", '"')
        
        # base64_encoding 설정
        if encode_option == "텍스트만":
            data["base64_encoding"] = '["text"]'
        elif encode_option == "표만":
            data["base64_encoding"] = '["table"]'
        elif encode_option == "텍스트와 표":
            data["base64_encoding"] = '["text","table"]'
        
        if st.button("파싱 실행", type="primary"):
            with st.spinner("파싱 중..."):
                files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            
            if resp.ok:
                result = resp.json()
                st.success("✅ 파싱 성공!")
                
                # 결과 요약
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("추출된 요소", len(result.get("elements", [])))
                with col2:
                    st.metric("처리된 페이지", result.get("usage", {}).get("pages", 0))
                with col3:
                    # 요소 타입 카운트
                    categories = {}
                    for elem in result.get("elements", []):
                        cat = elem.get("category", "unknown")
                        categories[cat] = categories.get(cat, 0) + 1
                    st.metric("요소 타입", len(categories))
                
                # 탭으로 결과 표시
                tabs = st.tabs(["📄 문서 뷰", "📊 표 추출", "📝 마크다운", "💾 다운로드", "🔍 원본 데이터"])
                
                # 문서 뷰 탭
                with tabs[0]:
                    st.subheader("렌더링된 문서")
                    
                    html_content = result.get("content", {}).get("html", "")
                    if html_content:
                        # CSS 스타일 추가
                        styled_html = f"""
                        <style>
                            .parsed-content {{
                                font-family: 'Noto Sans KR', sans-serif;
                                line-height: 1.6;
                                max-width: 800px;
                                margin: 0 auto;
                                padding: 20px;
                                background: white;
                                border-radius: 10px;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            }}
                            .parsed-content h1 {{ 
                                color: #2c3e50; 
                                border-bottom: 2px solid #3498db;
                                padding-bottom: 10px;
                                margin: 20px 0;
                            }}
                            .parsed-content h2 {{ 
                                color: #34495e;
                                margin: 15px 0;
                            }}
                            .parsed-content h3 {{ 
                                color: #7f8c8d;
                                margin: 10px 0;
                            }}
                            .parsed-content p {{
                                margin: 10px 0;
                                text-align: justify;
                            }}
                            .parsed-content table {{
                                border-collapse: collapse;
                                width: 100%;
                                margin: 20px 0;
                            }}
                            .parsed-content th, .parsed-content td {{
                                border: 1px solid #ddd;
                                padding: 8px;
                                text-align: left;
                            }}
                            .parsed-content th {{
                                background-color: #3498db;
                                color: white;
                            }}
                            .parsed-content tr:nth-child(even) {{
                                background-color: #f2f2f2;
                            }}
                        </style>
                        <div class="parsed-content">
                            {html_content}
                        </div>
                        """
                        st.markdown(styled_html, unsafe_allow_html=True)
                    
                    # Base64 인코딩된 이미지 표시
                    for elem in result.get("elements", []):
                        if elem.get("base64_encoding"):
                            cat = elem.get("category", "unknown")
                            st.write(f"**{cat} 이미지:**")
                            img_data = base64.b64decode(elem["base64_encoding"])
                            st.image(img_data, use_column_width=True)
                
                # 표 추출 탭
                with tabs[1]:
                    st.subheader("추출된 표")
                    
                    # HTML에서 표 추출
                    tables = extract_tables_from_html(html_content)
                    
                    if tables:
                        for i, table_data in enumerate(tables):
                            st.write(f"### 표 {i+1}")
                            
                            # 데이터프레임으로 변환
                            if len(table_data) > 1:
                                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            else:
                                df = pd.DataFrame(table_data)
                            
                            # 표 표시
                            st.dataframe(df, use_container_width=True)
                            
                            # CSV 다운로드
                            csv = df.to_csv(index=False)
                            st.download_button(
                                f"💾 표 {i+1} CSV 다운로드",
                                csv,
                                f"table_{i+1}.csv",
                                "text/csv",
                                key=f"csv_{i}"
                            )
                    else:
                        st.info("추출된 표가 없습니다.")
                
                # 마크다운 탭
                with tabs[2]:
                    st.subheader("마크다운 변환")
                    
                    # API에서 제공하는 마크다운 우선 사용
                    markdown_content = result.get("content", {}).get("markdown", "")
                    
                    # 없으면 HTML에서 변환
                    if not markdown_content and html_content:
                        markdown_content = html_to_markdown(html_content)
                    
                    if markdown_content:
                        # 마크다운 미리보기
                        st.markdown(markdown_content)
                        
                        # 편집 가능한 텍스트 영역
                        with st.expander("마크다운 편집"):
                            edited_md = st.text_area(
                                "마크다운 편집", 
                                markdown_content, 
                                height=400
                            )
                    else:
                        st.info("마크다운 콘텐츠가 없습니다.")
                
                # 다운로드 탭
                with tabs[3]:
                    st.subheader("다운로드 옵션")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # HTML 다운로드
                        if html_content:
                            # 완전한 HTML 문서 생성
                            full_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <meta charset="UTF-8">
                                <title>{uploaded.name} - Parsed</title>
                                <style>
                                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                                    table {{ border-collapse: collapse; width: 100%; }}
                                    th, td {{ border: 1px solid #ddd; padding: 8px; }}
                                    th {{ background-color: #4CAF50; color: white; }}
                                </style>
                            </head>
                            <body>
                                {html_content}
                            </body>
                            </html>
                            """
                            st.download_button(
                                "📄 HTML 다운로드",
                                full_html,
                                f"{uploaded.name.split('.')[0]}_parsed.html",
                                "text/html"
                            )
                    
                    with col2:
                        # 마크다운 다운로드
                        if markdown_content:
                            st.download_button(
                                "📝 마크다운 다운로드",
                                markdown_content,
                                f"{uploaded.name.split('.')[0]}_parsed.md",
                                "text/markdown"
                            )
                    
                    # JSON 다운로드
                    st.download_button(
                        "🔍 JSON 데이터 다운로드",
                        json.dumps(result, ensure_ascii=False, indent=2),
                        f"{uploaded.name.split('.')[0]}_parsed.json",
                        "application/json"
                    )
                
                # 원본 데이터 탭
                with tabs[4]:
                    st.subheader("원본 JSON 데이터")
                    st.json(result)
                    
            else:
                st.error(f"파싱 실패: {resp.status_code} - {resp.text}")

# ─── OCR 페이지 (기존 코드 유지) ─────────────────────────────────────────────
elif page == "OCR":
    st.header("🔍 OCR (Document OCR)")
    uploaded = st.file_uploader("PDF/이미지 파일 업로드", type=["pdf","png","jpg","jpeg"])
    if uploaded:
        st.write(f"파일명: {uploaded.name}")
        files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
        
        data = {
            "ocr": "force",
            "model": "document-parse"
        }
        
        if st.button("OCR 실행"):
            with st.spinner("OCR 처리 중..."):
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            if resp.ok:
                result = resp.json()
                st.success("OCR 완료!")
                
                html_content = result.get("content", {}).get("html", "")
                text_content = result.get("content", {}).get("text", "")
                
                if not text_content and html_content:
                    import re
                    text_content = html_content.replace('<br>', '\n').replace('<br/>', '\n')
                    text_content = re.sub('<[^<]+?>', '', text_content)
                    text_content = re.sub(r'[ \t]+', ' ', text_content).strip()
                
                st.code(text_content, language=None)
                
                st.download_button(
                    label="💾 텍스트 파일로 다운로드",
                    data=text_content,
                    file_name=f"{uploaded.name.split('.')[0]}_ocr.txt",
                    mime="text/plain"
                )
            else:
                st.error(f"OCR 실패: {resp.status_code} - {resp.text}")
