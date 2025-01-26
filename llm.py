from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain import hub
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import ChatOpenAI

def get_ai_message(user_message):
    # OpenAIEmbeddings: OpenAI Embedding 모델 "text-embedding-3-large"로 텍스트를 벡터화
    embedding = OpenAIEmbeddings(model="text-embedding-3-large")
    index_name = 'spring-index'

    #Pinecone에 이미 만들어진 인덱스('spring-index')를 불러옵니다. 이 인덱스에는 스프링 관련 문서(문서의 벡터)가 저장되어 있다고 가정
    database = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embedding)
    llm = ChatOpenAI(model='gpt-4o')
    prompt = hub.pull("rlm/rag-prompt")

    # PineconeVectorStore로부터 문서를 가져올 수 있는 Retriever 객체
    retriever = database.as_retriever()  # VectorStore에서 retriever 생성

    # 사용자의 질의에 맞춰 retriever를 통해 문서를 찾아보고, 그 문서를 참고해 LLM(GPT-4)을 사용하여 답변을 생성
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt}  # 필요한 경우 추가 인자 설정
    )

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
    spring_chain = {"query": chain} | qa_chain
    ai_message = spring_chain.invoke({"question": user_message})
    return ai_message

