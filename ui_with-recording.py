import streamlit as st
import speech_recognition as sr
from dotenv import load_dotenv
from llm import get_ai_response

load_dotenv()

def get_audio_input():
    # 음성 인식을 수행하고, 텍스트를 반환하는 함수
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("음성을 듣고 있습니다...")
        audio = r.listen(source)
    try:
        recognized_text = r.recognize_google(audio, language='ko')
        st.write(f"구글 음성 인식 결과: {recognized_text}")
        return recognized_text
    except sr.UnknownValueError:
        st.write("인식에 실패했습니다. 다시 시도해주세요.")
        return None
    except sr.RequestError as e:
        st.write(f"에러가 발생했습니다: {e}")
        return None
        
# Streamlit 기본 UI 세팅
st.set_page_config(page_title="스프링 메뉴얼 설명 봇", page_icon="🍃")
st.title("🍃 스프링 설명 챗봇")
st.caption("스프링 프레임워크에 관련된 모든 것을 답변해드립니다!")

# 세션에서 채팅 기록 관리
if "message_list" not in st.session_state:
    st.session_state["message_list"] = []

# 지금까지의 대화 내용 표시
for message in st.session_state["message_list"]:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 1) 마이크 버튼을 눌러 음성 인식
if st.button("마이크 켜기"):
    user_question = get_audio_input()
    if user_question is not None:
        # 1-1) 음성으로 인식된 텍스트를 "user" 메시지로 추가
        with st.chat_message("user"):
            st.write(user_question)
        st.session_state["message_list"].append({"role": "user", "content": user_question})

        # 1-2) LLM(또는 RAG 체인)에서 답변 생성
        with st.spinner("답변을 생성하는 중입니다..."):
            ai_response = get_ai_response(user_question)
        # 1-3) 챗봇 메시지 추가
        with st.chat_message("ai"):
            st.write(ai_response)
        st.session_state["message_list"].append({"role": "ai", "content": ai_response})

# 2) 텍스트 입력 (Chat Input)
if user_question := st.chat_input(placeholder="스프링 프레임워크에 관련된 궁금한 내용들을 말씀해주세요!"):
    # 2-1) 사용자 메시지
    with st.chat_message("user"):
        st.write(user_question)
    st.session_state["message_list"].append({"role": "user", "content": user_question})

    # 2-2) AI 답변 생성
    with st.spinner("답변을 생성하는 중입니다..."):
        ai_response = get_ai_response(user_question)
    # 2-3) 챗봇 메시지 추가
    with st.chat_message("ai"):
        st.write(ai_response)
    st.session_state["message_list"].append({"role": "ai", "content": ai_response})
