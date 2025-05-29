# app.py
import streamlit as st
from openai import OpenAI  # openai==1.52.2

# ─── Client 초기화 ─────────────────────────────────────────────────────────────
client = OpenAI(
    api_key=st.secrets["upstage_api_key"],
    base_url="https://api.upstage.ai/v1"
)

def chat_with_solar(messages):
    response = client.chat.completions.create(
        model="solar-pro",
        messages=messages
    )
    return response.choices[0].message.content

# ─── 세션 상태 초기화 ───────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    # system 메시지는 필요에 따라 설정하세요
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

st.title("🌞 Upstage Solar Chatbot")

# ─── 기존 대화 렌더링 ────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# ─── 사용자 입력 처리 ───────────────────────────────────────────────────────────
if prompt := st.chat_input("메시지를 입력하세요..."):
    # 1) 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    # 2) API 호출
    with st.spinner("응답 생성 중..."):
        reply = chat_with_solar(st.session_state.messages)
    # 3) 어시스턴트 메시지 추가
    st.session_state.messages.append({"role": "assistant", "content": reply})
    # 4) 페이지 리로드하여 새 메시지 표시
    st.experimental_rerun()
