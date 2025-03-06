import streamlit as st
from dotenv import load_dotenv
from llm import get_ai_response
import io
import speech_recognition as sr
import streamlit_audiorec  # 음성 녹음을 위한 커스텀 컴포넌트

load_dotenv()

st.set_page_config(page_title="자동차 정비 안내 봇", page_icon="🚗", layout="wide")

st.title("🚗 자동차 정비 챗봇")
st.caption("자동차 정비 과정 문의 및 메일/보고서 작성을 도와드립니다!")

# 버튼 스타일을 100% 너비로 적용하는 CSS 추가
st.markdown(
    """
    <style>
    .stButton button {
        width: 100%;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 세션 상태 초기화: 메시지 목록과 선택 모드
if 'message_list' not in st.session_state:
    st.session_state.message_list = []
if 'selected_mode' not in st.session_state:
    st.session_state.selected_mode = None

# 모드 선택 버튼: 정비 과정 문의 / 메일 또는 보고서 작성
col1, col2 = st.columns(2)
with col1:
    if st.button("정비 과정 문의"):
        st.session_state.selected_mode = "maintenance"
with col2:
    if st.button("메일/보고서 작성"):
        st.session_state.selected_mode = "report"

# 선택된 모드 안내
if st.session_state.selected_mode == "maintenance":
    st.info("정비 과정에 대한 문의를 진행합니다.")
elif st.session_state.selected_mode == "report":
    st.info("메일 또는 보고서 작성을 진행합니다.")
else:
    st.info("원하는 작업을 선택해주세요.")

# 기존 메시지 출력
for message in st.session_state.message_list:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# === 음성 입력 영역 추가 ===
st.markdown("### 음성 입력 (버튼을 눌러 음성을 녹음하세요)")
audio_bytes = streamlit_audiorec.audio_recorder()

if audio_bytes is not None:
    # 녹음된 음성 재생
    st.audio(audio_bytes, format="audio/wav")
    recognizer = sr.Recognizer()
    audio_file = sr.AudioFile(io.BytesIO(audio_bytes))
    with audio_file as source:
        audio_data = recognizer.record(source)
    try:
        # 음성을 텍스트로 변환 (한국어)
        voice_text = recognizer.recognize_google(audio_data, language="ko-KR")
        st.write("음성 인식 결과:", voice_text)
        # 음성 인식 결과를 채팅 메시지로 추가
        with st.chat_message("user"):
            st.write(voice_text)
        st.session_state.message_list.append({"role": "user", "content": voice_text})

        with st.spinner("답변을 생성하는 중입니다."):
            ai_response = get_ai_response(voice_text)
            with st.chat_message("ai"):
                st.write(ai_response)
            st.session_state.message_list.append({"role": "ai", "content": ai_response})
    except sr.UnknownValueError:
        st.error("음성을 인식하지 못했습니다. 다시 시도해주세요.")
    except sr.RequestError as e:
        st.error(f"음성 인식 서비스에 문제가 있습니다: {e}")

# === 텍스트 채팅 입력 영역 ===
if st.session_state.selected_mode == "maintenance":
    placeholder_text = "정비 과정에 대해 궁금한 내용을 입력해주세요!"
elif st.session_state.selected_mode == "report":
    placeholder_text = "메일 또는 보고서 작성 관련 문의 내용을 입력해주세요!"
else:
    placeholder_text = "문의할 내용을 입력해주세요!"

if user_question := st.chat_input(placeholder=placeholder_text):
    with st.chat_message("user"):
        st.write(user_question)
    st.session_state.message_list.append({"role": "user", "content": user_question})

    with st.spinner("답변을 생성하는 중입니다."):
        ai_response = get_ai_response(user_question)
        with st.chat_message("ai"):
            st.write(ai_response)
        st.session_state.message_list.append({"role": "ai", "content": ai_response})
