import streamlit as st
import requests

# 페이지 구성 및 API 설정
st.set_page_config(page_title="📄 Upstage Multi-Tool", layout="wide")
api_key = st.secrets["upstage_api_key"]
base_url = "https://api.upstage.ai/v1"

# 사이드바 네비게이션
st.sidebar.title("🔧 기능 선택")
page = st.sidebar.radio("페이지 선택", ["문서 파싱", "OCR", "정보 추출"])

# 공통 헤더
headers = {"Authorization": f"Bearer {api_key}"}

# ─── 문서 파싱 페이지 ───────────────────────────────────────────────────────────
if page == "문서 파싱":
    st.header("📄 문서 파싱 (Document Parsing)")
    uploaded = st.file_uploader("PDF/이미지 파일 업로드", type=["pdf","png","jpg","jpeg"])
    if uploaded:
        st.write(f"파일명: {uploaded.name}")
        files = {"document": (uploaded.name, uploaded.read(), uploaded.type)}
        
        # base64_encoding 옵션 선택
        encode_option = st.selectbox(
            "Base64 인코딩 옵션",
            ["없음", "텍스트만", "테이블만", "텍스트와 테이블"]
        )
        
        data = {
            "ocr": "auto",
            "model": "document-parse"
        }
        
        # base64_encoding 설정
        if encode_option == "텍스트만":
            data["base64_encoding"] = '["text"]'
        elif encode_option == "테이블만":
            data["base64_encoding"] = '["table"]'
        elif encode_option == "텍스트와 테이블":
            data["base64_encoding"] = '["text","table"]'
        
        if st.button("파싱 실행"):
            with st.spinner("파싱 중..."):
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            if resp.ok:
                result = resp.json()
                st.success("파싱 완료!")
                st.json(result)
            else:
                st.error(f"파싱 실패: {resp.status_code} - {resp.text}")

# ─── OCR 페이지 ─────────────────────────────────────────────────────────────────
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
                
                # HTML 콘텐츠에서 텍스트 추출
                html_content = result.get("content", {}).get("html", "")
                text_content = result.get("content", {}).get("text", "")
                
                # text가 비어있으면 HTML에서 추출
                if not text_content and html_content:
                    import re
                    # HTML 태그 제거 및 줄바꿈 보존
                    text_content = html_content.replace('<br>', '\n').replace('<br/>', '\n')
                    text_content = re.sub('<[^<]+?>', '', text_content)
                    text_content = re.sub(r'[ \t]+', ' ', text_content).strip()
                
                # 결과 표시 옵션
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader("📝 추출된 텍스트")
                with col2:
                    # 복사 버튼 (JavaScript 사용)
                    if st.button("📋 전체 복사", type="primary"):
                        st.write("아래 텍스트를 전체 선택(Ctrl+A) 후 복사(Ctrl+C)하세요")
                
                # 텍스트 표시 방법 선택
                display_option = st.radio(
                    "표시 방법",
                    ["텍스트 영역 (수정 가능)", "코드 블록 (복사 버튼 포함)", "일반 텍스트"],
                    horizontal=True
                )
                
                if display_option == "텍스트 영역 (수정 가능)":
                    # 수정 가능한 텍스트 영역
                    edited_text = st.text_area(
                        "텍스트를 수정할 수 있습니다:",
                        text_content,
                        height=400,
                        help="텍스트를 선택하고 Ctrl+C(또는 Cmd+C)로 복사할 수 있습니다."
                    )
                    
                    # 수정된 텍스트 다운로드
                    if edited_text != text_content:
                        st.download_button(
                            label="💾 수정된 텍스트 다운로드",
                            data=edited_text,
                            file_name=f"{uploaded.name.split('.')[0]}_ocr_edited.txt",
                            mime="text/plain"
                        )
                
                elif display_option == "코드 블록 (복사 버튼 포함)":
                    # 자동 복사 버튼이 있는 코드 블록
                    st.code(text_content, language=None)
                
                else:  # 일반 텍스트
                    # 일반 텍스트로 표시
                    st.text(text_content)
                
                # 원본 텍스트 다운로드 버튼
                st.download_button(
                    label="💾 텍스트 파일로 다운로드",
                    data=text_content,
                    file_name=f"{uploaded.name.split('.')[0]}_ocr.txt",
                    mime="text/plain"
                )
                
                # 통계 정보
                with st.expander("📊 텍스트 통계"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("총 문자 수", f"{len(text_content):,}")
                    with col2:
                        st.metric("단어 수", f"{len(text_content.split()):,}")
                    with col3:
                        st.metric("줄 수", f"{len(text_content.splitlines()):,}")
                
                # 전체 응답 데이터
                with st.expander("🔍 전체 응답 데이터 보기"):
                    st.json(result)
            else:
                st.error(f"OCR 실패: {resp.status_code} - {resp.text}")

# ─── 정보 추출 페이지 ─────────────────────────────────────────────────────────────
elif page == "정보 추출":
    st.header("🔎 정보 추출 (Information Extraction)")
    text_input = st.text_area("추출할 텍스트 입력", height=200)
    if st.button("정보 추출 실행"):
        payload = {
            "model": "universal",
            "text": text_input
        }
        with st.spinner("정보 추출 중..."):
            resp = requests.post(
                f"{base_url}/information-extraction/universal",
                headers={**headers, "Content-Type": "application/json"},
                json=payload
            )
        if resp.ok:
            result = resp.json()
            st.success("추출 완료!")
            st.json(result)
        else:
            st.error(f"추출 실패: {resp.status_code} - {resp.text}")
