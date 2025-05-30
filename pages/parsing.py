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
            data["base64_encoding"] = '["text"]'  # JSON 형식의 큰따옴표 사용
        elif encode_option == "테이블만":
            data["base64_encoding"] = '["table"]'
        elif encode_option == "텍스트와 테이블":
            data["base64_encoding"] = '["text","table"]'
        # "없음"인 경우 base64_encoding 파라미터를 아예 포함하지 않음
        
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
        
        # base64_encoding 없이 시도
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
                    # HTML 태그 제거
                    text_content = re.sub('<[^<]+?>', ' ', html_content)
                    text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                st.text_area("추출된 텍스트", text_content, height=300)
                
                # 전체 결과도 확인할 수 있도록 표시
                with st.expander("전체 응답 데이터 보기"):
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
