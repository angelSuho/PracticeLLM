# %%
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

embedding_function = OpenAIEmbeddings(model='text-embedding-3-large')

vector_store = Chroma (
    embedding_function=embedding_function,
    collection_name='spring_framework_docs',
    persist_directory='./spring_framework_docs'
)
retriever = vector_store.as_retriever(search_kwargs={'k': 3})

# %%
from typing_extensions import List, TypedDict
from langchain_core.documents import Document
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    query: str
    context: List[Document]
    answer: str

graph_builder = StateGraph(AgentState)

# %%
# Node는 2가지가 필요
# 1. 문서를 가져오는 retrieve
# 2. 답변을 생성하는 generate

def retrieve(state: AgentState):
    query = state['query']
    docs = retriever.invoke(query)
    return {'context': docs}

# %%
# set the LANGSMITH_API_KEY environment variable (create key in settings)
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model='gpt-4o')

# %%
from langchain import hub
from langchain_core.output_parsers import StrOutputParser

# prompt는 genereate, rewrite, 문서 관련성 등 프롬포트가 필요하다.
# 따라서 prompt라는 이름으로는 중복 변수 이름이 될 수 있다.
generate_prompt = hub.pull("rlm/rag-prompt")
generate_llm = ChatOpenAI(model='gpt-4o', max_completion_tokens=100)

def generate(state: AgentState):
    context = state['context']
    query = state['query']
    rag_chain = generate_prompt | generate_llm # | StrOutputParser
    response = rag_chain.invoke({'question': query, 'context': context})
    return {'answer': response.content}

# %%
from langchain import hub
from typing import Literal
doc_relevance_prompt = hub.pull("langchain-ai/rag-document-relevance")

def check_doc_relevance(state: AgentState) -> Literal['relevant', 'irrelevant']:
    query = state['query']
    context = state['context']
    print(f'context = {context}')
    doc_relevance_chain = doc_relevance_prompt | llm
    response = doc_relevance_chain.invoke({'question': query, 'documents': context})
    print(f'doc relevance response: {response}')
    if response['Score'] == 1:
        return 'relevant'
    return 'irrelevant'

# %%
from langchain_core.prompts import PromptTemplate

dictionary = ['사용자와 관련된 표현 -> 클라이언트']
rewrite_prompt = PromptTemplate.from_template(f"""
사용자의 질문을 보고, 우리의 사전을 참고해서 사용자의 질문을 변경해주세요.
사전: {dictionary}
질문: {{query}}
""")

# 입력된 쿼리(query)를 변형(rewrite)하여 새로운 쿼리를 생성하는 것
def rewrite(state: AgentState):
    query = state['query']
    rewrite_chain = rewrite_prompt | llm
    response = rewrite_chain.invoke({'query': query})
    return {'query': response.content}

# %%
from langchain import hub
from langchain_core.output_parsers import StrOutputParser

# hallucination_prompt = hub.pull("langchain-ai/rag-answer-hallucination")
hallucination_prompt = PromptTemplate.from_template("""
You are a teacher tasked with evaluating whether a student's answer is based on documents or not,
Given documents, which are excerpts from income tax law, and a student's answer; 
If the student's answer is based on documents, respond with "not hallucinated",                                             
If the student's answer is not based on documents, respond with "hallucinated".
                                                    
documents: {documents}
student_answer: {student_answer}
                                                
""")

hallucination_llm = ChatOpenAI(model='gpt-4o', temperature=0)
def check_hallucination(state: AgentState) -> Literal['hallucinated', 'not hallucinated']:
    answer = state['answer']
    context = state['context']
    context = [doc.page_content for doc in context]
    print(f'context = {context}')
    hallucination_chain = hallucination_prompt | hallucination_llm # | StrOutputParser
    response = hallucination_chain.invoke({'student_answer': answer, 'documents': context})
    print(f'hallucination response: {response}')
    return response.content

# %%
# set the LANGSMITH_API_KEY environment variable (create key in settings)
from langchain import hub
helpfulness_prompt = hub.pull("langchain-ai/rag-answer-helpfulness") 

def check_helpfulness_grader(state: AgentState) :
    query = state['query']
    answer = state['answer']
    helpfulness_chain = helpfulness_prompt | llm
    response = helpfulness_chain.invoke({'question': query, 'student_answer': answer})
    print(f'helpfulness response: {response}')
    if response['Score'] == 1:
        return 'helpful'
    return 'unhelpful'

def check_helpfulness(state: AgentState) :
    return state 

# %%
query = "Bean Factory와 Application Context의 차이는 무엇인가요?"
context = retriever.invoke(query)
generate_state = {'query': query, 'context': context}
answer = generate(generate_state)
print(f'answer == {answer}')
# hallucination_state = {'answer': answer, 'context': context}

helpfulness_state = {'query': query, 'answer': answer}
# check_hallucination(hallucination_state)
check_helpfulness(helpfulness_state)

# %%
graph_builder.add_node('retrieve', retrieve)
graph_builder.add_node('generate', generate)
# graph_builder.add_node('check_doc_relevance', check_doc_relevance)
graph_builder.add_node('rewrite', rewrite)
# graph_builder.add_node('check_hallucination', check_hallucination)
graph_builder.add_node('check_helpfulness', check_helpfulness)

# %%
from langgraph.graph import START, END

graph_builder.add_edge(START, 'retrieve')
graph_builder.add_conditional_edges(
    'retrieve',
    check_doc_relevance, {
        'relevant': 'generate',
        'irrelevant': END
    }
)
graph_builder.add_conditional_edges(
    'generate',
    check_hallucination, {
        'not hallucinated': 'check_helpfulness',
        'hallucinated': 'generate'
    }
)
graph_builder.add_conditional_edges(
    'check_helpfulness',
    check_helpfulness_grader, {
        'helpful': END,
        'unhelpful': 'rewrite'
    }
)
graph_builder.add_edge('rewrite', 'retrieve')

# %%
graph = graph_builder.compile()

