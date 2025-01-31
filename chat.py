import streamlit as st

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain import hub
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from deep_translator import GoogleTranslator

load_dotenv()

def translate_text(text, source, target):
    return GoogleTranslator(source=source, target=target).translate(text)

def get_ai_message(user_message):
    translator = GoogleTranslator(source="ko", target="en")
    translated_message = translator.translate(user_message)
    print(translated_message)

    if translated_message.lower() in ["안녕하세요", "반갑습니다"]:
        return {"result": "안녕하세요! 무엇을 도와드릴까요?"}

    embedding = OpenAIEmbeddings(model="text-embedding-3-large")
    index_name = 'spring-index'
    database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding)
    llm = ChatOpenAI(model='gpt-4o')
    prompt = hub.pull("rlm/rag-prompt")

    retriever = database.as_retriever()  # VectorStore에서 retriever 생성
    search_results = retriever.get_relevant_documents(translated_message)

    # 검색 결과가 없을 경우 기본 응답 반환
    print(search_results)
    if not search_results or max([doc.metadata.get('score', 0) for doc in search_results]) < 0.8:
        return {"result": "스프링 프레임워크와 관련된 질문을 요청해주세요!"}

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt}  # 필요한 경우 추가 인자 설정
    )

    dictionary = ["언어를 나타내는 표현 -> 자바"]

    prompt = ChatPromptTemplate.from_template(
        f"""
        사용자의 질문을 보고, 우리의 사전을 참고해서 사용자의 질문을 변경해주세요.
        만약 변경할 필요가 없다고 판단된다면, 사용자의 질문을 변경하지 않아도 됩니다.

        당신의 답변은 Korean(한글)으로 말해주세요.

        사전: {dictionary}

        질문: {{question}}
        """
    )

    chain = prompt | llm | StrOutputParser()
    spring_chain = {"query": chain} | qa_chain
    ai_message = spring_chain.invoke({"question": user_message})

    translator = GoogleTranslator(source="en", target="ko")
    translated_response = translator.translate(ai_message)

    return {"result": translated_response}

st.set_page_config(page_title="스프링 메뉴얼 설명 봇", page_icon="🍃")

st.title("🍃 스프링 설명 챗봇")
st.caption("스프링 프레임워크에 관련된 모든것을 답변해드립니다!")

if 'message_list' not in st.session_state:
    st.session_state.message_list = []
for message in st.session_state.message_list:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_question := st.chat_input(placeholder="스프링 프레임워크에 관련된 궁금한 내용들을 말씀해주세요!"):
    with st.chat_message("user"):
        st.write(user_question)
    st.session_state.message_list.append({"role": "user", "content": user_question})

    ai_message = get_ai_message(user_question)
    with st.chat_message("ai"):
            st.write(ai_message["result"])
    st.session_state.message_list.append({"role": "ai", "content": ai_message["result"]})