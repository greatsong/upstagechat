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
        # base64_encoding을 문자열 형태의 리스트로 전달
        data = {
            "ocr": "auto",
            "base64_encoding": "['text', 'table']",  # 문자열로 리스트 표현
            "model": "document-parse"
        }
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
            "base64_encoding": "['text']",  # 문자열로 리스트 표현
            "model": "document-parse"
        }
        if st.button("OCR 실행"):
            with st.spinner("OCR 처리 중..."):
                resp = requests.post(f"{base_url}/document-digitization", headers=headers, files=files, data=data)
            if resp.ok:
                result = resp.json()
                st.success("OCR 완료!")
                # content 내의 text 추출
                text_content = result.get("content", {}).get("text", "")
                if not text_content and "elements" in result:
                    # elements에서 텍스트 추출
                    texts = []
                    for elem in result["elements"]:
                        elem_text = elem.get("content", {}).get("text", "")
                        if elem_text:
                            texts.append(elem_text)
                    text_content = "\n".join(texts)
                
                st.text_area("추출된 텍스트", text_content, height=300)
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
