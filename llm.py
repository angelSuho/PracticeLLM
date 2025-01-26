from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, FewShotChatMessagePromptTemplate, PromptTemplate

# from langchain.chains import RetrievalQA
# from langchain import hub

from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from config import answer_examples

store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]



def get_retriever():
    # OpenAIEmbeddings: OpenAI Embedding 모델 "text-embedding-3-large"로 텍스트를 벡터화
    embedding = OpenAIEmbeddings(model="text-embedding-3-large")
    index_name = 'spring-index'
    #Pinecone에 이미 만들어진 인덱스('spring-index')를 불러옵니다. 이 인덱스에는 스프링 관련 문서(문서의 벡터)가 저장되어 있다고 가정
    database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding)
    # PineconeVectorStore로부터 문서를 가져올 수 있는 Retriever 객체
    retriever = database.as_retriever()  # VectorStore에서 retriever 생성
    return retriever


def get_history_retriever():
    llm = get_llm()
    retriever = get_retriever()

    # langchain 내부적으로 효율성이 좋은 프롬포트를 모아 hub에 저장, 이후 그것을 가져와 사용
    # prompt = hub.pull("rlm/rag-prompt")

    contextualize_q_system_prompt = """Given a chat history and the latest user question \
        which might reference context in the chat history, formulate a standalone question \
        which can be understood without the chat history. Do NOT answer the question, \
        just reformulate it if needed and otherwise return it as is."""
    
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    return history_aware_retriever


def get_llm(model='gpt-4o'):
    llm = ChatOpenAI(model=model)
    return llm


def get_dictionary_chain():
    llm = get_llm()

    # 사용자의 질문을 수정(혹은 보정)할 때 참고할 수 있는 '사전' 데이터.
    # 예: "언어"라는 표현이 들어오면 "자바"를 의미한다고 해석할 수 있게끔 사전을 두는 식의 예시
    dictionary = ["언어를 나타내는 표현 -> 자바"]
    prompt = ChatPromptTemplate.from_template(
    f"""
    사용자의 질문을 보고, 우리의 사전을 참고해서 사용자의 질문을 변경해주세요.
    만약 변경할 필요가 없다고 판단된다면, 사용자의 질문을 변경하지 않아도 됩니다.

    당신의 답변은 Korean(한글)으로 말해주세요.

    사전: {dictionary}

    질문: {{question}}
    """)

    # 주석 
    """
    - prompt | llm | StrOutputParser() → 이 파이프라인은
        1. prompt: 사용자 질문을 prompt 템플릿에 넣어 완성
        2. llm(GPT-4): prompt에 따라 답변(즉 질문 수정안)을 생성
        3. StrOutputParser(): 답변(문자열)을 파싱
    - 이 결과물(수정된 질문)을 {"query": chain} 형태로 지정하여 qa_chain(RetrievalQA)에 연결
    - 즉, 최종적으로 spring_chain은
        1. 사용자 질문을 사전에 따라 수정
        2. 수정된 질문을 PineconeRetriever로 검색
        3. 검색된 문서를 바탕으로 GPT-4가 최종 답변
    """
    chain = prompt | llm | StrOutputParser()
    return chain


def get_rag_chain():
    llm = get_llm()

    # 사용자의 질의에 맞춰 retriever를 통해 문서를 찾아보고, 그 문서를 참고해 LLM(GPT-4)을 사용하여 답변을 생성
    # qa_chain = RetrievalQA.from_chain_type(
    #     llm=llm,
    #     retriever=retriever,
    #     chain_type_kwargs={"prompt": prompt}  # 필요한 경우 추가 인자 설정
    # )
    # return qa_chain
    
    example_prompt = ChatPromptTemplate.from_messages(
        [
            ("human", "{input}"),
            ("ai", "{answer}"),
        ]
    )

    # 채팅의 예시를 알려주어 보다 정확도를 매우 향상시키는 few_shot 적용
    few_shot_prompt = FewShotChatMessagePromptTemplate(
        example_prompt=example_prompt,
        examples=answer_examples,
    )

    qa_system_prompt = """
        You are an expert Spring Framework backend developer. \
        Please refer to the provided documentation to answer the question. \
        If you do not know the answer, simply say you do not know. \
        Provide a concise, key-point answer in no more than three sentences. \

        {context}
    """

    qa_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", qa_system_prompt),
            few_shot_prompt,
            MessagesPlaceholder("chat_history"),
            ("human", "{input}"),
        ]
    )

    history_aware_retriever = get_history_retriever()
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    ).pick("answer")
    # 이때 answer와 같은 결과는 변수명을 맞춰주어야함. ex) result, output, answer 등

    return conversational_rag_chain


def get_ai_response(user_message):
    dictionary_chain = get_dictionary_chain()
    rag_chain = get_rag_chain()

    spring_chain = {"input": dictionary_chain} | rag_chain
    ai_response = spring_chain.stream(
        {
            "question": user_message
        },
        config={
            "configurable": {"session_id": "abc123"}
        },
    )
    return ai_response

