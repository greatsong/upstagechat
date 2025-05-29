# app.py
import streamlit as st
import requests

st.set_page_config(page_title="📄 Document OCR & Chat", layout="wide")
st.title("🌞 Upstage Solar + Document Digitization")

# ─── Secrets에서 API 키 불러오기 ─────────────────────────────────────────────
api_key = st.secrets["upstage_api_key"]
base_chat_url = "https://api.upstage.ai/v1"
doc_url = f"{base_chat_url}/document-digitization"

# ─── Session State 초기화 ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# ─── 사이드바: 파일 업로드 & OCR 옵션 ─────────────────────────────────────────
with st.sidebar:
    st.header("OCR 설정")
    uploaded_file = st.file_uploader("📎 문서 업로드", type=["pdf", "png", "jpg", "jpeg"])
    use_ocr = st.checkbox("강제 OCR(force)", value=True)
    extract_tables = st.checkbox("테이블만 추출", value=True)
    if uploaded_file and st.button("OCR 실행"):
        files = {"document": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
        data = {
            "ocr": "force" if use_ocr else "auto",
            "base64_encoding": "['table']" if extract_tables else "['text','table']",
            "model": "document-parse"
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        with st.spinner("문서 처리 중..."):
            resp = requests.post(doc_url, headers=headers, files=files, data=data)
        if resp.ok:
            result = resp.json()
            st.success("OCR 완료!")
            st.json(result)
            # OCR 결과를 대화 히스토리에 추가하려면 아래처럼 사용 가능합니다.
            # text_content = result.get("text", "")
            # st.session_state.messages.append({"role": "user", "content": text_content})
        else:
            st.error(f"OCR 실패: {resp.status_code} / {resp.text}")

# ─── 메인: Chat 인터페이스 ────────────────────────────────────────────────────
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("메시지를 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 여기에 chat_with_solar 호출 로직을 추가하세요.
    # 예: reply = chat_with_solar(st.session_state.messages)
    reply = "아직 챗 기능은 연결되지 않았습니다."  # placeholder
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
