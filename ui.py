import streamlit as st
from dotenv import load_dotenv

from llm import get_ai_response

load_dotenv()

st.set_page_config(page_title="스프링 메뉴얼 설명 봇", page_icon="🍃")

st.title("🍃 스프링 설명 챗봇")
st.caption("스프링 프레임워크에 관련된 모든것을 답변해드립니다!")

if 'message_list' not in st.session_state:
    st.session_state.message_list = []
for message in st.session_state.message_list:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 채팅 입력
if user_question := st.chat_input(placeholder="스프링 프레임워크에 관련된 궁금한 내용들을 말씀해주세요!"):
    with st.chat_message("user"):
        st.write(user_question)
    st.session_state.message_list.append({"role": "user", "content": user_question})

    with st.spinner("답변을 생성하는 중입니다."):
        ai_response = get_ai_response(user_question)
        with st.chat_message("ai"):
            ai_response = st.write_stream(ai_response)
            st.session_state.message_list.append({"role": "ai", "content": ai_response})
