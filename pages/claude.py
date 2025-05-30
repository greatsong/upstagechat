import streamlit as st
import requests
import json
import pandas as pd
from io import BytesIO
import base64
import re

# 페이지 구성 및 API 설정
st.set_page_config(page_title="📄 Upstage Document Tool", layout="wide")
api_key = st.secrets["upstage_api_key"]
base_url = "https://api.upstage.ai/v1"

# 사이드바 네비게이션
st.sidebar.title("🔧 기능 선택")
page = st.sidebar.radio("페이지 선택", ["문서 파싱", "OCR"])

# 지원 파일 형식
st.sidebar.markdown("### 📋 지원 파일 형식")
st.sidebar.info("""
**확실히 지원:**
- PDF
- PNG, JPG, JPEG

**테스트 필요:**
- HWP (한글 문서)
- DOCX (워드)
- PPTX (파워포인트)
- XLSX (엑셀)
""")

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
    
    # 파일 업로더 - HWP 및 기타 형식 추가
    uploaded = st.file_uploader(
        "문서 파일 업로드", 
        type=["pdf", "png", "jpg", "jpeg", "hwp", "docx", "pptx", "xlsx"],
        help="PDF와 이미지는 확실히 지원됩니다. HWP, DOCX 등은 테스트가 필요합니다."
    )
    
    if uploaded:
        # 파일 정보 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("파일명", uploaded.name)
        with col2:
            st.metric("파일 크기", f"{uploaded.size / 1024:.1f} KB")
        with col3:
            file_ext = uploaded.name.split('.')[-1].upper()
            st.metric("파일 형식", file_ext)
        
        # HWP 파일 경고
        if file_ext == "HWP":
            st.warning("⚠️ HWP 파일은 테스트가 필요합니다. 지원되지 않을 수 있습니다.")
        
        # 옵션 설정
        col1, col2 = st.columns(2)
        with col1:
            encode_option = st.selectbox(
                "Base64 인코딩 옵션",
                ["없음", "표만", "텍스트만", "텍스트와 표", "모든 요소"]
            )
        with col2:
            output_format = st.multiselect(
                "출력 형식",
                ["html", "text", "markdown"],
                default=["html", "markdown"]
            )
        
        # 고급 옵션
        with st.expander("⚙️ 고급 옵션"):
            col1, col2 = st.columns(2)
            with col1:
                ocr_mode = st.selectbox(
                    "OCR 모드",
                    ["auto (자동)", "force (강제)"],
                    help="auto: 필요시에만 OCR, force: 항상 OCR"
                )
                coordinates = st.checkbox("좌표 정보 포함", value=True)
            with col2:
                chart_recognition = st.checkbox("차트 인식", value=True)
        
        # API 파라미터 구성
        data = {
            "ocr": ocr_mode.split()[0],
            "model": "document-parse",
            "coordinates": str(coordinates).lower(),
            "chart_recognition": str(chart_recognition).lower()
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
        elif encode_option == "모든 요소":
            data["base64_encoding"] = '["text","table","figure","chart","diagram","heading1","heading2","heading3","paragraph","list"]'
        
        # 현재 설정 표시
        with st.expander("📋 API 파라미터 확인"):
            st.json(data)
        
        if st.button("🚀 파싱 실행", type="primary"):
            with st.spinner(f"{file_ext} 파일 파싱 중..."):
                files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            
            if resp.ok:
                result = resp.json()
                st.success(f"✅ {file_ext} 파일 파싱 성공!")
                
                # 결과 요약
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("추출된 요소", len(result.get("elements", [])))
                with col2:
                    st.metric("처리된 페이지", result.get("usage", {}).get("pages", 0))
                with col3:
                    categories = {}
                    for elem in result.get("elements", []):
                        cat = elem.get("category", "unknown")
                        categories[cat] = categories.get(cat, 0) + 1
                    st.metric("요소 타입", len(categories))
                
                # 탭으로 결과 표시
                tabs = st.tabs(["📄 문서 뷰", "📊 표 추출", "📝 마크다운", "🖼️ 이미지/도표", "💾 다운로드", "🔍 원본 데이터"])
                
                # 문서 뷰 탭
                with tabs[0]:
                    st.subheader("렌더링된 문서")
                    
                    html_content = result.get("content", {}).get("html", "")
                    if html_content:
                        styled_html = f"""
                        <style>
                            .parsed-content {{
                                font-family: 'Noto Sans KR', sans-serif;
                                line-height: 1.6;
                                max-width: 900px;
                                margin: 0 auto;
                                padding: 30px;
                                background: white;
                                border-radius: 10px;
                                box-shadow: 0 2px 20px rgba(0,0,0,0.1);
                            }}
                            .parsed-content h1 {{ 
                                color: #1a1a1a; 
                                border-bottom: 3px solid #0066cc;
                                padding-bottom: 10px;
                                margin: 30px 0 20px 0;
                                font-size: 28px;
                            }}
                            .parsed-content h2 {{ 
                                color: #333;
                                margin: 25px 0 15px 0;
                                font-size: 22px;
                            }}
                            .parsed-content h3 {{ 
                                color: #555;
                                margin: 20px 0 10px 0;
                                font-size: 18px;
                            }}
                            .parsed-content p {{
                                margin: 15px 0;
                                line-height: 1.8;
                                color: #444;
                            }}
                            .parsed-content table {{
                                border-collapse: collapse;
                                width: 100%;
                                margin: 20px 0;
                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            }}
                            .parsed-content th, .parsed-content td {{
                                border: 1px solid #ddd;
                                padding: 12px;
                                text-align: left;
                            }}
                            .parsed-content th {{
                                background-color: #0066cc;
                                color: white;
                                font-weight: bold;
                            }}
                            .parsed-content tr:nth-child(even) {{
                                background-color: #f8f9fa;
                            }}
                            .parsed-content tr:hover {{
                                background-color: #e9ecef;
                            }}
                        </style>
                        <div class="parsed-content">
                            {html_content}
                        </div>
                        """
                        st.markdown(styled_html, unsafe_allow_html=True)
                    else:
                        st.info("HTML 콘텐츠가 없습니다.")
                
                # 표 추출 탭
                with tabs[1]:
                    st.subheader("추출된 표")
                    
                    tables = extract_tables_from_html(html_content)
                    
                    if tables:
                        for i, table_data in enumerate(tables):
                            st.write(f"### 표 {i+1}")
                            
                            if len(table_data) > 1:
                                df = pd.DataFrame(table_data[1:], columns=table_data[0])
                            else:
                                df = pd.DataFrame(table_data)
                            
                            st.dataframe(df, use_container_width=True)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                csv = df.to_csv(index=False, encoding='utf-8-sig')
                                st.download_button(
                                    f"💾 CSV 다운로드",
                                    csv.encode('utf-8-sig'),
                                    f"table_{i+1}.csv",
                                    "text/csv",
                                    key=f"csv_{i}"
                                )
                            with col2:
                                # 엑셀 다운로드
                                buffer = BytesIO()
                                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                    df.to_excel(writer, index=False, sheet_name=f'Table_{i+1}')
                                buffer.seek(0)
                                st.download_button(
                                    f"💾 Excel 다운로드",
                                    buffer,
                                    f"table_{i+1}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key=f"excel_{i}"
                                )
                    else:
                        st.info("추출된 표가 없습니다.")
                
                # 마크다운 탭
                with tabs[2]:
                    st.subheader("마크다운 변환")
                    
                    markdown_content = result.get("content", {}).get("markdown", "")
                    
                    if not markdown_content and html_content:
                        markdown_content = html_to_markdown(html_content)
                    
                    if markdown_content:
                        st.markdown("### 미리보기")
                        st.markdown(markdown_content)
                        
                        st.markdown("### 편집")
                        edited_md = st.text_area(
                            "마크다운 편집", 
                            markdown_content, 
                            height=400
                        )
                        
                        if edited_md != markdown_content:
                            st.download_button(
                                "💾 편집된 마크다운 다운로드",
                                edited_md,
                                f"{uploaded.name.split('.')[0]}_edited.md",
                                "text/markdown"
                            )
                    else:
                        st.info("마크다운 콘텐츠가 없습니다.")
                
                # 이미지/도표 탭
                with tabs[3]:
                    st.subheader("추출된 이미지 및 도표")
                    
                    image_elements = []
                    for elem in result.get("elements", []):
                        if elem.get("base64_encoding"):
                            image_elements.append(elem)
                    
                    if image_elements:
                        for i, elem in enumerate(image_elements):
                            cat = elem.get("category", "unknown")
                            st.write(f"### {cat.upper()} {i+1}")
                            
                            try:
                                img_data = base64.b64decode(elem["base64_encoding"])
                                st.image(img_data, use_column_width=True)
                                
                                st.download_button(
                                    f"💾 {cat}_{i+1} 다운로드",
                                    img_data,
                                    f"{cat}_{i+1}.png",
                                    "image/png",
                                    key=f"img_{i}"
                                )
                            except Exception as e:
                                st.error(f"이미지 디코딩 오류: {str(e)}")
                            
                            st.divider()
                    else:
                        st.info("Base64 인코딩된 이미지가 없습니다. Base64 인코딩 옵션을 설정해주세요.")
                
                # 다운로드 탭
                with tabs[4]:
                    st.subheader("전체 문서 다운로드")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if html_content:
                            full_html = f"""
                            <!DOCTYPE html>
                            <html>
                            <head>
                                <meta charset="UTF-8">
                                <title>{uploaded.name} - Parsed</title>
                                <style>
                                    body {{ 
                                        font-family: 'Malgun Gothic', sans-serif; 
                                        margin: 40px;
                                        line-height: 1.6;
                                    }}
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
                        if markdown_content:
                            st.download_button(
                                "📝 마크다운 다운로드",
                                markdown_content,
                                f"{uploaded.name.split('.')[0]}_parsed.md",
                                "text/markdown"
                            )
                    
                    with col3:
                        st.download_button(
                            "🔍 JSON 다운로드",
                            json.dumps(result, ensure_ascii=False, indent=2),
                            f"{uploaded.name.split('.')[0]}_parsed.json",
                            "application/json"
                        )
                
                # 원본 데이터 탭
                with tabs[5]:
                    st.subheader("원본 JSON 응답")
                    st.json(result)
                    
            else:
                st.error(f"❌ 파싱 실패: {resp.status_code}")
                error_msg = resp.json() if resp.headers.get('content-type') == 'application/json' else resp.text
                st.error(f"오류 메시지: {error_msg}")
                
                # 파일 형식별 오류 처리
                if file_ext == "HWP":
                    st.info("""
                    💡 **HWP 파일 오류 해결 방법:**
                    1. HWP를 PDF로 변환 후 업로드
                    2. 한글 프로그램에서 "다른 이름으로 저장" → PDF 선택
                    3. 온라인 HWP→PDF 변환 서비스 이용
                    """)
                elif "too many pages" in str(error_msg).lower():
                    st.info("""
                    💡 **페이지 수 초과 해결 방법:**
                    1. 문서를 여러 부분으로 나누기
                    2. 필요한 페이지만 추출하여 새 PDF 생성
                    3. 온라인 PDF 분할 도구 사용
                    """)
                elif "unsupported" in str(error_msg).lower():
                    st.info(f"""
                    💡 **{file_ext} 형식 미지원:**
                    - 지원 형식: PDF, PNG, JPG, JPEG
                    - 다른 형식으로 변환 후 시도해주세요
                    """)

# ─── OCR 페이지 ─────────────────────────────────────────────────────────────────
elif page == "OCR":
    st.header("🔍 OCR (텍스트 추출)")
    
    uploaded = st.file_uploader(
        "문서/이미지 파일 업로드", 
        type=["pdf", "png", "jpg", "jpeg", "hwp", "docx"],
        help="이미지나 스캔된 문서에서 텍스트를 추출합니다"
    )
    
    if uploaded:
        # 파일 정보
        col1, col2 = st.columns(2)
        with col1:
            st.metric("파일명", uploaded.name)
        with col2:
            st.metric("파일 크기", f"{uploaded.size / 1024:.1f} KB")
        
        files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
        
        data = {
            "ocr": "force",
            "model": "document-parse"
        }
        
        if st.button("🔍 OCR 실행", type="primary"):
            with st.spinner("텍스트 추출 중..."):
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            
            if resp.ok:
                result = resp.json()
                st.success("✅ OCR 완료!")
                
                # 텍스트 추출
                html_content = result.get("content", {}).get("html", "")
                text_content = result.get("content", {}).get("text", "")
                
                if not text_content and html_content:
                    text_content = html_content.replace('<br>', '\n').replace('<br/>', '\n')
                    text_content = re.sub('<[^<]+?>', '', text_content)
                    text_content = re.sub(r'[ \t]+', ' ', text_content).strip()
                
                # 통계
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("총 문자 수", f"{len(text_content):,}")
                with col2:
                    st.metric("단어 수", f"{len(text_content.split()):,}")
                with col3:
                    st.metric("줄 수", f"{len(text_content.splitlines()):,}")
                
                # 텍스트 표시
                st.subheader("추출된 텍스트")
                st.code(text_content, language=None)
                
                # 다운로드
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="💾 TXT 다운로드",
                        data=text_content,
                        file_name=f"{uploaded.name.split('.')[0]}_ocr.txt",
                        mime="text/plain"
                    )
                with col2:
                    # 워드 형식으로도 저장 가능하도록
                    st.download_button(
                        label="💾 복사용 텍스트",
                        data=text_content,
                        file_name=f"{uploaded.name.split('.')[0]}_text.txt",
                        mime="text/plain"
                    )
            else:
                st.error(f"❌ OCR 실패: {resp.status_code} - {resp.text}")
                
                file_ext = uploaded.name.split('.')[-1].upper()
                if file_ext in ["HWP", "DOCX"]:
                    st.info(f"""
                    💡 **{file_ext} 파일 처리 실패 시:**
                    1. PDF로 변환 후 다시 시도
                    2. 이미지(PNG/JPG)로 저장 후 업로드
                    """)
