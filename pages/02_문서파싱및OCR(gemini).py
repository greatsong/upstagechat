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
        
        max_cols = 0
        if table_data: # Ensure table_data is not empty before finding max_cols
            # Filter out empty rows or rows with non-iterable elements before calculating max_cols
            valid_rows = [row for row in table_data if hasattr(row, '__len__')]
            if valid_rows:
                 max_cols = max(len(row) for row in valid_rows)
            else: # if all rows are invalid or table_data was initially empty after filtering
                return pd.DataFrame()


        normalized_data = []
        for row in table_data: # Iterate original table_data for normalization
            if hasattr(row, '__len__'): # Process only if row is iterable
                 normalized_row = list(row) + [''] * (max_cols - len(row)) # Ensure row is list for extendability
                 normalized_data.append(normalized_row)
            # else: skip rows that are not iterable or handle as error/empty

        if not normalized_data: # If no data could be normalized
            return pd.DataFrame()

        if len(normalized_data) > 1 and len(normalized_data[0]) == max_cols:
            df = pd.DataFrame(normalized_data[1:], columns=normalized_data[0])
        else:
            df = pd.DataFrame(normalized_data)
        
        return df
        
    except Exception as e:
        st.error(f"DataFrame 생성 오류: {str(e)}")
        return pd.DataFrame(table_data) # Fallback to original data if error

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
    
    uploaded_file = st.file_uploader(
        "문서 파일 업로드", 
        type=["pdf", "png", "jpg", "jpeg", "hwp", "docx", "pptx", "xlsx"],
        help="PDF와 이미지는 확실히 지원됩니다. HWP, DOCX 등은 테스트가 필요합니다."
    )
    
    if uploaded_file:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("파일명", uploaded_file.name)
        with col2:
            st.metric("파일 크기", f"{uploaded_file.size / 1024:.1f} KB")
        with col3:
            file_ext = uploaded_file.name.split('.')[-1].upper()
            st.metric("파일 형식", file_ext)
        
        col1_opts, col2_opts = st.columns(2) # Renamed to avoid conflict with col1, col2 above
        with col1_opts:
            encode_option = st.selectbox(
                "Base64 인코딩 옵션",
                ["없음", "표만", "텍스트만", "텍스트와 표", "모든 요소"],
                key=f"encode_opt_{uploaded_file.name}"
            )
        with col2_opts:
            output_format = st.multiselect(
                "출력 형식",
                ["html", "text", "markdown"],
                default=["html"],
                key=f"output_fmt_{uploaded_file.name}"
            )
        
        with st.expander("⚙️ 고급 옵션"):
            col1_adv, col2_adv = st.columns(2) # Renamed for clarity
            with col1_adv:
                ocr_mode = st.selectbox(
                    "OCR 모드",
                    ["auto (자동)", "force (강제)"],
                    help="auto: 필요시에만 OCR, force: 항상 OCR",
                    key=f"ocr_mode_{uploaded_file.name}"
                )
                coordinates = st.checkbox("좌표 정보 포함", value=True, key=f"coords_{uploaded_file.name}")
            with col2_adv:
                chart_recognition = st.checkbox("차트 인식", value=True, key=f"chart_recog_{uploaded_file.name}")
        
        api_data = { # Renamed 'data' to 'api_data'
            "ocr": ocr_mode.split()[0],
            "model": "document-parse",
            "coordinates": str(coordinates).lower(),
            "chart_recognition": str(chart_recognition).lower()
        }
        
        if output_format:
            api_data["output_formats"] = str(output_format).replace("'", '"')
        
        if encode_option == "텍스트만":
            api_data["base64_encoding"] = '["text"]'
        elif encode_option == "표만":
            api_data["base64_encoding"] = '["table"]'
        elif encode_option == "텍스트와 표":
            api_data["base64_encoding"] = '["text","table"]'
        elif encode_option == "모든 요소":
            api_data["base64_encoding"] = '["text","table","figure","chart","diagram","heading1","heading2","heading3","paragraph","list"]'
        
        with st.expander("📋 API 파라미터 확인"):
            st.json(api_data)
        
        if st.button("🚀 파싱 실행", type="primary", key=f"parse_btn_{uploaded_file.name}"):
            with st.spinner(f"{file_ext} 파일 파싱 중..."):
                files_payload = {"document": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)} # Renamed 'files'
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files_payload, data=api_data)
            
            if resp.ok:
                result = resp.json()
                st.success(f"✅ {file_ext} 파일 파싱 성공!")
                
                res_col1, res_col2, res_col3 = st.columns(3) # Renamed for summary
                with res_col1:
                    st.metric("추출된 요소", len(result.get("elements", [])))
                with res_col2:
                    st.metric("처리된 페이지", result.get("usage", {}).get("pages", 0))
                with res_col3:
                    categories = {}
                    for elem in result.get("elements", []):
                        cat = elem.get("category", "unknown")
                        categories[cat] = categories.get(cat, 0) + 1
                    st.metric("요소 타입", len(categories))
                
                tabs = st.tabs(["📄 문서 뷰", "📊 표 추출", "📝 마크다운", "🖼️ 이미지/도표", "💾 다운로드", "🔍 원본 데이터"])
                
                html_content = result.get("content", {}).get("html", "")
                markdown_content = result.get("content", {}).get("markdown", "")
                if not markdown_content and html_content:
                    markdown_content = html_to_markdown(html_content)

                with tabs[0]:
                    st.subheader("렌더링된 문서")
                    if html_content:
                        styled_html = f"""
                        <style>
                            .parsed-content {{ font-family: 'Noto Sans KR', sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 2px 20px rgba(0,0,0,0.1);}}
                            .parsed-content h1 {{ color: #1a1a1a; border-bottom: 3px solid #0066cc; padding-bottom: 10px; margin: 30px 0 20px 0; font-size: 28px;}}
                            .parsed-content h2 {{ color: #333; margin: 25px 0 15px 0; font-size: 22px;}}
                            .parsed-content h3 {{ color: #555; margin: 20px 0 10px 0; font-size: 18px;}}
                            .parsed-content p {{ margin: 15px 0; line-height: 1.8; color: #444;}}
                            .parsed-content table {{ border-collapse: collapse; width: 100%; margin: 20px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.1);}}
                            .parsed-content th, .parsed-content td {{ border: 1px solid #ddd; padding: 12px; text-align: left;}}
                            .parsed-content th {{ background-color: #0066cc; color: white; font-weight: bold;}}
                            .parsed-content tr:nth-child(even) {{ background-color: #f8f9fa;}}
                            .parsed-content tr:hover {{ background-color: #e9ecef;}}
                        </style>
                        <div class="parsed-content">{html_content}</div>"""
                        st.markdown(styled_html, unsafe_allow_html=True)
                    else:
                        st.info("HTML 콘텐츠가 없습니다.")
                
                with tabs[1]:
                    st.subheader("추출된 표")
                    tables = extract_tables_from_html(html_content)
                    if tables:
                        for i, table_data in enumerate(tables):
                            st.write(f"### 표 {i+1}")
                            df = safe_create_dataframe(table_data)
                            if not df.empty:
                                st.dataframe(df, use_container_width=True)
                                df_col1, df_col2 = st.columns(2) # Renamed
                                with df_col1:
                                    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig') # Renamed 'csv'
                                    st.download_button(f"💾 CSV 다운로드", csv_data, f"table_{i+1}.csv", "text/csv", key=f"csv_{i}_{uploaded_file.name}")
                                with df_col2:
                                    try:
                                        buffer = BytesIO()
                                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                                            df.to_excel(writer, index=False, sheet_name=f'Table_{i+1}')
                                        buffer.seek(0)
                                        st.download_button(f"💾 Excel 다운로드", buffer, f"table_{i+1}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"excel_{i}_{uploaded_file.name}")
                                    except Exception as e:
                                        st.error(f"Excel 변환 오류: {str(e)}")
                            else:
                                st.warning(f"표 {i+1}을 DataFrame으로 변환할 수 없습니다.")
                                st.text("원본 데이터:")
                                for row in table_data:
                                    st.text(" | ".join(str(cell) for cell in row)) # Ensure cells are strings
                    else:
                        st.info("추출된 표가 없습니다.")
                
                with tabs[2]:
                    st.subheader("마크다운 변환")
                    if markdown_content:
                        st.markdown("### 미리보기")
                        st.markdown(markdown_content)
                        st.markdown("### 편집")
                        edited_md = st.text_area("마크다운 편집", markdown_content, height=400, key=f"md_edit_{uploaded_file.name}")
                        if edited_md != markdown_content:
                            st.download_button("💾 편집된 마크다운 다운로드", edited_md.encode('utf-8'), f"{uploaded_file.name.split('.')[0]}_edited.md", "text/markdown", key=f"md_download_edited_{uploaded_file.name}")
                    else:
                        st.info("마크다운 콘텐츠가 없습니다.")
                
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
                                st.download_button(f"💾 {cat}_{i+1} 다운로드", img_data, f"{cat}_{i+1}.png", "image/png", key=f"img_{i}_{uploaded_file.name}")
                            except Exception as e:
                                st.error(f"이미지 디코딩 오류: {str(e)}")
                            st.divider()
                    else:
                        st.info("Base64 인코딩된 이미지가 없습니다. Base64 인코딩 옵션을 설정해주세요.")
                
                with tabs[4]:
                    st.subheader("전체 문서 다운로드")
                    dl_all_col1, dl_all_col2, dl_all_col3 = st.columns(3) # Renamed
                    with dl_all_col1:
                        if html_content:
                            full_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{uploaded_file.name} - Parsed</title><style>body {{ font-family: 'Malgun Gothic', sans-serif; margin: 40px; line-height: 1.6;}} table {{ border-collapse: collapse; width: 100%; }} th, td {{ border: 1px solid #ddd; padding: 8px; }} th {{ background-color: #4CAF50; color: white; }}</style></head><body>{html_content}</body></html>"""
                            st.download_button("📄 HTML 다운로드", full_html.encode('utf-8'), f"{uploaded_file.name.split('.')[0]}_parsed.html", "text/html", key=f"html_full_download_{uploaded_file.name}")
                    with dl_all_col2:
                        if markdown_content:
                            st.download_button("📝 마크다운 다운로드", markdown_content.encode('utf-8'), f"{uploaded_file.name.split('.')[0]}_parsed.md", "text/markdown", key=f"md_full_download_{uploaded_file.name}")
                    with dl_all_col3:
                        json_str = json.dumps(result, ensure_ascii=False, indent=2)
                        st.download_button("🔍 JSON 다운로드", json_str.encode('utf-8'), f"{uploaded_file.name.split('.')[0]}_parsed.json", "application/json", key=f"json_full_download_{uploaded_file.name}")
                
                with tabs[5]:
                    st.subheader("원본 JSON 응답")
                    st.json(result)
            else:
                st.error(f"❌ 파싱 실패: {resp.status_code}")
                try:
                    error_msg = resp.json()
                except json.JSONDecodeError: # More specific exception
                    error_msg = resp.text
                st.error(f"오류 메시지: {error_msg}")
                if file_ext == "HWP":
                    st.info("""💡 **HWP 파일 오류 해결 방법:**\n1. HWP를 PDF로 변환 후 업로드\n2. 한글 프로그램에서 "다른 이름으로 저장" → PDF 선택\n3. 온라인 HWP→PDF 변환 서비스 이용""")

# ─── OCR 페이지 (수정됨) ─────────────────────────────────────────────────────────
elif page == "OCR":
    st.header("🔍 OCR (텍스트 추출)")
    
    uploaded_files = st.file_uploader(
        "문서/이미지 파일 업로드 (여러 파일 선택 가능)", 
        type=["pdf", "png", "jpg", "jpeg", "hwp", "docx"],
        accept_multiple_files=True,
        help="이미지나 스캔된 문서에서 텍스트를 추출합니다. 여러 파일을 한 번에 올릴 수 있습니다."
    )
    
    if uploaded_files:
        for uploaded_file_item in uploaded_files: # Changed loop variable name
            with st.expander(f"📄 {uploaded_file_item.name} ({(uploaded_file_item.size / 1024):.1f} KB) 결과", expanded=True):
                
                files_data_ocr = {"document": (uploaded_file_item.name, uploaded_file_item.read(), uploaded_file_item.type)} # Renamed
                
                api_params_ocr = { # Renamed
                    "ocr": "force",
                    "model": "document-parse"
                }
                
                button_key_ocr = f"ocr_button_{uploaded_file_item.name}_{uploaded_file_item.size}" # Added size for more uniqueness
                if st.button("🔍 OCR 실행", type="primary", key=button_key_ocr):
                    with st.spinner(f"{uploaded_file_item.name} 텍스트 추출 중..."):
                        resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files_data_ocr, data=api_params_ocr)
                    
                    if resp.ok:
                        result_ocr = resp.json() # Renamed
                        st.success(f"✅ {uploaded_file_item.name}: OCR 완료!")
                        
                        html_content_ocr = result_ocr.get("content", {}).get("html", "") # Renamed
                        text_content_ocr = result_ocr.get("content", {}).get("text", "") # Renamed
                        
                        if not text_content_ocr and html_content_ocr:
                            temp_text = html_content_ocr.replace('<br>', '\n').replace('<br/>', '\n')
                            temp_text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', temp_text) 
                            temp_text = re.sub('<[^<]+?>', '', temp_text) 
                            text_content_ocr = re.sub(r'[ \t]+', ' ', temp_text).strip()
                            text_content_ocr = "\n".join([line.strip() for line in text_content_ocr.splitlines() if line.strip()])

                        if text_content_ocr:
                            ocr_stat_col1, ocr_stat_col2, ocr_stat_col3 = st.columns(3) # Renamed
                            with ocr_stat_col1:
                                st.metric("총 문자 수", f"{len(text_content_ocr):,}", key=f"char_cnt_{uploaded_file_item.name}_{uploaded_file_item.size}")
                            with ocr_stat_col2:
                                st.metric("단어 수", f"{len(text_content_ocr.split()):,}", key=f"word_cnt_{uploaded_file_item.name}_{uploaded_file_item.size}")
                            with ocr_stat_col3:
                                st.metric("줄 수", f"{len(text_content_ocr.splitlines()):,}", key=f"line_cnt_{uploaded_file_item.name}_{uploaded_file_item.size}")
                            
                            st.subheader("추출된 텍스트")
                            st.text_area(
                                label="추출된 텍스트 내용:", # Changed label from " "
                                value=text_content_ocr, 
                                height=300, 
                                key=f"text_area_{uploaded_file_item.name}_{uploaded_file_item.size}", 
                                disabled=True
                            )
                            
                            st.markdown("##### 💾 다운로드")
                            ocr_dl_col1, ocr_dl_col2 = st.columns(2) # Renamed
                            with ocr_dl_col1:
                                st.download_button(
                                    label="TXT 파일 (.txt)",
                                    data=text_content_ocr.encode('utf-8'),
                                    file_name=f"{uploaded_file_item.name.split('.')[0]}_ocr.txt",
                                    mime="text/plain",
                                    key=f"txt_dl_{uploaded_file_item.name}_{uploaded_file_item.size}"
                                )
                            with ocr_dl_col2:
                                try:
                                    docx_bytes = text_to_docx_bytes(text_content_ocr)
                                    st.download_button(
                                        label="Word 파일 (.docx)",
                                        data=docx_bytes,
                                        file_name=f"{uploaded_file_item.name.split('.')[0]}_ocr.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key=f"docx_dl_{uploaded_file_item.name}_{uploaded_file_item.size}"
                                    )
                                except Exception as e:
                                    st.error(f"DOCX 변환 오류: {e}")
                        else:
                            st.info("추출된 텍스트가 없습니다.")
                            st.json(result_ocr)

                    else:
                        st.error(f"❌ {uploaded_file_item.name}: OCR 실패 (상태 코드: {resp.status_code})")
                        try:
                            error_detail = resp.json()
                        except json.JSONDecodeError: # More specific exception
                            error_detail = resp.text
                        st.error(f"오류 내용: {error_detail}")
                st.divider()
    else:
        st.info("OCR을 실행할 파일을 업로드해주세요.")
