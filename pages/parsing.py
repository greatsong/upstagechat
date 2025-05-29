# app.py
# app.py
import streamlit as st
from openai import OpenAI
import requests

# ─── 페이지 설정 ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="🌞 Upstage Solar Chat & OCR", layout="wide")
st.title("📄 Upstage Solar Chat & Document OCR")
st.markdown("🛠️ 이 앱은 **석리송**이 만들었어요! 🎉")

# ─── API 클라이언트 초기화 ───────────────────────────────────────────────────
api_key     = st.secrets["upstage_api_key"]
chat_client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
doc_url     = "https://api.upstage.ai/v1/document-digitization"

def chat_with_solar(messages):
    resp = chat_client.chat.completions.create(
        model="solar-pro",
        messages=messages
    )
    return resp.choices[0].message.content

# ─── 세션 상태 초기화 ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# ─── 레이아웃: 왼쪽 채팅 · 오른쪽 OCR ────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.header("💬 Chat")
    # 대화 내역 표시
    for msg in st.session_state.messages:
        role = "You" if msg["role"] == "user" else "Assistant"
        st.markdown(f"**{role}:** {msg['content']}")

    # 사용자 입력
    user_input = st.text_input("메시지를 입력하고 ▶ 눌러 보내세요", key="input")
    if st.button("▶ Send"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.spinner("응답 생성 중…"):
            reply = chat_with_solar(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        # 입력창 비우기
        st.session_state.input = ""
        st.experimental_rerun()

with col2:
    st.header("📎 Document OCR")
    uploaded_file = st.file_uploader("파일 업로드 (PDF • PNG • JPG)", type=["pdf","png","jpg","jpeg"])
    if uploaded_file:
        force = st.checkbox("강제 OCR (force)", value=True)
        tables = st.checkbox("테이블만 추출", value=False)
        if st.button("OCR 실행"):
            files = {"document": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
            data = {
                "ocr": "force" if force else "auto",
                "base64_encoding": "['table']" if tables else "['text','table']",
                "model": "document-parse"
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            with st.spinner("문서 처리 중…"):
                resp = requests.post(doc_url, headers=headers, files=files, data=data)
            if resp.ok:
                st.success("✅ OCR 완료!")
                st.json(resp.json())
            else:
                st.error(f"❌ OCR 실패: {resp.status_code}")

# ─── 사용법 안내 ─────────────────────────────────────────────────────────────
st.markdown("""
**사용 방법 요약**  
1. `.streamlit/secrets.toml`에 API 키를 넣으세요:
   ```toml
   upstage_api_key = "YOUR_UPSTAGE_API_KEY"
