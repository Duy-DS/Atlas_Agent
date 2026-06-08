import os

import streamlit as st

from ollama_chat_client import stream_chat


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.5:0.8b")


st.set_page_config(page_title="Atlas LLM Chat", page_icon="", layout="centered")
st.title("Atlas LLM Chat")
st.caption(f"Model: {MODEL_NAME}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Nhap cau hoi cho model...")

if prompt:
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        answer = ""
        try:
            for token in stream_chat(OLLAMA_BASE_URL, MODEL_NAME, st.session_state.messages):
                answer += token
                placeholder.markdown(answer)
        except Exception as exc:
            answer = f"Khong goi duoc Ollama: {exc}"
            placeholder.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
