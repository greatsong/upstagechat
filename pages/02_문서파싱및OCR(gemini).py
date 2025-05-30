안녕하세요! 요청하신 대로 OCR 기능에서 한 번에 여러 파일을 업로드하고, 각 파일의 OCR 결과를 텍스트(TXT) 및 워드(DOCX) 형식으로 다운로드할 수 있도록 코드를 수정했습니다.

주요 변경 사항은 다음과 같습니다:

1.  **다중 파일 업로드**: OCR 페이지에서 `st.file_uploader`에 `accept_multiple_files=True` 옵션을 추가하여 여러 파일을 동시에 업로드할 수 있도록 변경했습니다.
2.  **개별 파일 처리 및 결과 표시**: 업로드된 각 파일에 대해 OCR API를 호출하고, 파일명과 함께 `st.expander`를 사용하여 각 파일의 결과를 개별적으로 표시합니다.
3.  **다양한 형식 다운로드**:
    * 각 파일의 OCR 결과에 대해 텍스트 파일(.txt)로 다운로드할 수 있는 버튼을 제공합니다.
    * `python-docx` 라이브러리를 사용하여 추출된 텍스트를 Word 문서(.docx) 형식으로 다운로드할 수 있는 기능을 추가했습니다. 이를 위해 코드 상단에 `from docx import Document`를 추가하고, 텍스트를 DOCX 바이트로 변환하는 함수를 정의했습니다.
4.  **오류 처리**: 각 파일 처리 중 발생하는 API 오류를 개별적으로 표시합니다.

**참고**: DOCX 파일 생성을 위해 `python-docx` 라이브러리가 필요합니다. 만약 이 코드를 로컬 환경이나 Streamlit Cloud 등에서 실행하신다면, 해당 라이브러리를 설치해야 합니다.
(`pip install python-docx`)

수정된 코드는 아래와 같습니다.

```python
import streamlit as st
import requests
import json
import pandas as pd
from io import BytesIO
import base64
import re
from docx import Document # DOCX 처리를 위해 추가

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

# 안전한 DataFrame 생성 함수
def safe_create_dataframe(table_data):
    """안전하게 DataFrame 생성"""
    try:
        if not table_data:
            return pd.DataFrame()
        
        # 모든 행의 열 개수 확인
        max_cols = max(len(row) for row in table_data)
        
        # 모든 행을 같은 길이로 맞춤
        normalized_data = []
        for row in table_data:
            normalized_row = row + [''] * (max_cols - len(row))
            normalized_data.append(normalized_row)
        
        # 첫 번째 행을 헤더로 사용할 수 있는지 확인
        if len(normalized_data) > 1:
            # 첫 번째 행을 헤더로 사용
            df = pd.DataFrame(normalized_data[1:], columns=normalized_data[0])
        else:
            # 헤더 없이 생성
            df = pd.DataFrame(normalized_data)
        
        return df
        
    except Exception as e:
        st.error(f"DataFrame 생성 오류: {str(e)}")
        # 오류 발생 시 원본 데이터 그대로 반환
        return pd.DataFrame(table_data)

# 텍스트를 DOCX 파일 바이트로 변환하는 함수
def text_to_docx_bytes(text_content):
    doc = Document()
    doc.add_paragraph(text_content)
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio.getvalue()

# ─── 문서 파싱 페이지 ───────────────────────────────────────────────────────────
if page == "문서 파싱":
    st.header("📄 문서 파싱 (Document Parsing)")
    
    # 파일 업로더 - HWP 및 기타 형식 추가
    uploaded_file = st.file_uploader( # 변수명을 uploaded_file (단수)로 유지
        "문서 파일 업로드", 
        type=["pdf", "png", "jpg", "jpeg", "hwp", "docx", "pptx", "xlsx"],
        help="PDF와 이미지는 확실히 지원됩니다. HWP, DOCX 등은 테스트가 필요합니다."
    )
    
    if uploaded_file: # 단일 파일 처리
        # 파일 정보 표시
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("파일명", uploaded_file.name)
        with col2:
            st.metric("파일 크기", f"{uploaded_file.size / 1024:.1f} KB")
        with col3:
            file_ext = uploaded_file.name.split('.')[-1].upper()
            st.metric("파일 형식", file_ext)
        
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
                default=["html"]
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
                files = {"document": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
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
                
                html_content = result.get("content", {}).get("html", "") # html_content 정의 위치 이동
                markdown_content = result.get("content", {}).get("markdown", "") # markdown_content 정의 위치 이동
                if not markdown_content and html_content: # 마크다운이 없고 HTML이 있으면 변환 시도
                    markdown_content = html_to_markdown(html_content)

                # 문서 뷰 탭
                with tabs[0]:
                    st.subheader("렌더링된 문서")
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
                            df = safe_create_dataframe(table_data)
                            if not df.empty:
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
                                    try:
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
                                    except Exception as e:
                                        st.error(f"Excel 변환 오류: {str(e)}")
                            else:
                                st.warning(f"표 {i+1}을 DataFrame으로 변환할 수 없습니다.")
                                st.text("원본 데이터:")
                                for row in table_data:
                                    st.text(" | ".join(row))
                    else:
                        st.info("추출된 표가 없습니다.")
                
                # 마크다운 탭
                with tabs[2]:
                    st.subheader("마크다운 변환")
                    if markdown_content:
                        st.markdown("### 미리보기")
                        st.markdown(markdown_content)
                        st.markdown("### 편집")
                        edited_md = st.text_area(
                            "마크다운 편집", 
                            markdown_content, 
                            height=400,
                            key=f"md_edit_{uploaded_file.name}" 
                        )
                        if edited_md != markdown_content:
                            st.download_button(
                                "💾 편집된 마크다운 다운로드",
                                edited_md,
                                f"{uploaded_file.name.split('.')[0]}_edited.md",
                                "text/markdown",
                                key=f"md_download_{uploaded_file.name}"
                            )
                    else:
                        st.info("마크다운 콘텐츠가 없습니다.")
                
                # 이미지/도표 탭
                with tabs[3]:
                    st.subheader("추출된 이미지 및 도표")
                    image_elements = [elem for elem in result.get("elements", []) if elem.get("base64_encoding")]
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
                            <html><head><meta charset="UTF-8"><title>{uploaded_file.name} - Parsed</title>
                            <style>body {{ font-family: 'Malgun Gothic', sans-serif; margin: 40px; line-height: 1.6;}}
                            table {{ border-collapse: collapse; width: 100%; }}
                            th, td {{ border: 1px solid #ddd; padding: 8px; }}
                            th {{ background-color: #4CAF50; color: white; }}</style></head>
                            <body>{html_content}</body></html>
                            """
                            st.download_button(
                                "📄 HTML 다운로드",
                                full_html,
                                f"{uploaded_file.name.split('.')[0]}_parsed.html",
                                "text/html",
                                key=f"html_download_{uploaded_file.name}"
                            )
                    with col2:
                        if markdown_content:
                            st.download_button(
                                "📝 마크다운 다운로드",
                                markdown_content,
                                f"{uploaded_file.name.split('.')[0]}_parsed.md",
                                "text/markdown",
                                key=f"parsed_md_download_{uploaded_file.name}"
                            )
                    with col3:
                        st.download_button(
                            "🔍 JSON 다운로드",
                            json.dumps(result, ensure_ascii=False, indent=2),
                            f"{uploaded_file.name.split('.')[0]}_parsed.json",
                            "application/json",
                            key=f"json_download_{uploaded_file.name}"
                        )
                
                # 원본 데이터 탭
                with tabs[5]:
                    st.subheader("원본 JSON 응답")
                    st.json(result)
            else:
                st.error(f"❌ 파싱 실패: {resp.status_code}")
                try:
                    error_msg = resp.json()
                except:
                    error_msg = resp.text
                st.error(f"오류 메시지: {error_msg}")
                if file_ext == "HWP":
                    st.info("""
                    💡 **HWP 파일 오류 해결 방법:**
                    1. HWP를 PDF로 변환 후 업로드
                    2. 한글 프로그램에서 "다른 이름으로 저장" → PDF 선택
                    3. 온라인 HWP→PDF 변환 서비스 이용
                    """)

# ─── OCR 페이지 (수정됨) ─────────────────────────────────────────────────────────
elif page == "OCR":
    st.header("🔍 OCR (텍스트 추출)")
    
    uploaded_files = st.file_uploader(
        "문서/이미지 파일 업로드 (여러 파일 선택 가능)", 
        type=["pdf", "png", "jpg", "jpeg", "hwp", "docx"],
        accept_multiple_files=True, # 여러 파일 업로드 허용
        help="이미지나 스캔된 문서에서 텍스트를 추출합니다. 여러 파일을 한 번에 올릴 수 있습니다."
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            with st.expander(f"📄 {uploaded_file.name} ({(uploaded_file.size / 1024):.1f} KB) 결과", expanded=True):
                # 파일 정보 (expander 내부에 표시)
                # st.write(f"**파일명:** {uploaded_file.name}")
                # st.write(f"**파일 크기:** {uploaded_file.size / 1024:.1f} KB")
                
                files_data = {"document": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
                
                api_params = { # API 파라미터 명칭 변경 (data -> api_params)
                    "ocr": "force",
                    "model": "document-parse"
                }
                
                # 각 파일별로 버튼에 고유 key를 부여하기 위해 파일명을 사용
                button_key = f"ocr_button_{uploaded_file.name}"
                if st.button("🔍 OCR 실행", type="primary", key=button_key):
                    with st.spinner(f"{uploaded_file.name} 텍스트 추출 중..."):
                        resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files_data, data=api_params)
                    
                    if resp.ok:
                        result = resp.json()
                        st.success(f"✅ {uploaded_file.name}: OCR 완료!")
                        
                        # 텍스트 추출
                        html_content = result.get("content", {}).get("html", "")
                        text_content = result.get("content", {}).get("text", "")
                        
                        if not text_content and html_content:
                            # HTML에서 순수 텍스트 추출 (간단 버전)
                            temp_text = html_content.replace('<br>', '\n').replace('<br/>', '\n')
                            temp_text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', temp_text) # p 태그는 줄바꿈으로
                            temp_text = re.sub('<[^<]+?>', '', temp_text) # 나머지 태그 제거
                            text_content = re.sub(r'[ \t]+', ' ', temp_text).strip()
                            text_content = "\n".join([line.strip() for line in text_content.splitlines() if line.strip()]) # 빈 줄 제거 및 각 줄 앞뒤 공백 제거

                        if text_content:
                            # 통계
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("총 문자 수", f"{len(text_content):,}", key=f"char_count_{uploaded_file.name}")
                            with col2:
                                st.metric("단어 수", f"{len(text_content.split()):,}", key=f"word_count_{uploaded_file.name}")
                            with col3:
                                st.metric("줄 수", f"{len(text_content.splitlines()):,}", key=f"line_count_{uploaded_file.name}")
                            
                            # 텍스트 표시
                            st.subheader("추출된 텍스트")
                            st.text_area(" ",value=text_content, height=300, key=f"text_area_{uploaded_file.name}", disabled=True)
                            
                            # 다운로드 버튼들
                            st.markdown("##### 💾 다운로드")
                            dl_col1, dl_col2 = st.columns(2)
                            with dl_col1:
                                st.download_button(
                                    label="TXT 파일 (.txt)",
                                    data=text_content.encode('utf-8'), # UTF-8로 인코딩
                                    file_name=f"{uploaded_file.name.split('.')[0]}_ocr.txt",
                                    mime="text/plain",
                                    key=f"txt_download_{uploaded_file.name}"
                                )
                            with dl_col2:
                                try:
                                    docx_bytes = text_to_docx_bytes(text_content)
                                    st.download_button(
                                        label="Word 파일 (.docx)",
                                        data=docx_bytes,
                                        file_name=f"{uploaded_file.name.split('.')[0]}_ocr.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key=f"docx_download_{uploaded_file.name}"
                                    )
                                except Exception as e:
                                    st.error(f"DOCX 변환 오류: {e}")
                        else:
                            st.info("추출된 텍스트가 없습니다.")
                            st.json(result) # 텍스트가 없을 경우 원본 응답 표시

                    else:
                        st.error(f"❌ {uploaded_file.name}: OCR 실패 (상태 코드: {resp.status_code})")
                        try:
                            error_detail = resp.json()
                        except json.JSONDecodeError:
                            error_detail = resp.text
                        st.error(f"오류 내용: {error_detail}")
                st.divider() # 각 파일 expander 사이에 구분선 추가
    else:
        st.info("OCR을 실행할 파일을 업로드해주세요.")

```
