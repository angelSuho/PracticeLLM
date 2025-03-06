from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.types import Command
from typing import Literal
from langchain_core.messages import HumanMessage
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool
from langgraph.prebuilt import create_react_agent
from langchain_community.agent_toolkits.polygon.toolkit import PolygonToolkit
from langchain_community.utilities.polygon import PolygonAPIWrapper
import yfinance as yf
from langchain.tools import tool
from langchain_core.prompts import PromptTemplate
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.types import Command

load_dotenv()

llm = ChatOpenAI(model='gpt-4o')
small_llm = ChatOpenAI(model='gpt-4o-mini')

polygon = PolygonAPIWrapper()
toolkit = PolygonToolkit.from_polygon_api_wrapper(polygon)
polygon_tools = toolkit.get_tools()
market_research_tools = [YahooFinanceNewsTool()] + polygon_tools
market_research_agent = create_react_agent(
    llm,
    tools=market_research_tools,
    state_modifier='You are a market researcher. Provide fact only not opinions'
)


def market_research_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    result = market_research_agent.invoke(state)
    # print(f'market_research_node: {result}')
    return Command( 
        update={'messages': [HumanMessage(content=result['messages'][-1].content, name='market_research')]},
        goto='stock_research'
    )


@tool
def get_stock_price(ticker: str) -> str:
    """Given a stock ticker, return the price data for the past Month""" # 10 days
    stock_info = yf.download(ticker, period='1mo').to_dict() # 10d
    return stock_info


stock_research_tools = [get_stock_price]
stock_research_agent = create_react_agent(
    llm, tools=stock_research_tools, state_modifier='You are a stock researcher. Provide facts only not opinions'
)


def stock_research_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    result = stock_research_agent.invoke(state)
    # print(f'stock_research_node: {result}')
    return Command(
        update={'messages': [HumanMessage(content=result['messages'][-1].content, name='stock_research')]},
        goto='supervisor'
    )


@tool
def company_research_tool(ticker: str) -> dict:
    """Given a ticker, return the financial information and SEC filings"""
    company_info = yf.Ticker(ticker).info
    finacial_info = company_info.get_financials()
    sec_filings = company_info.get_sec_filings()
    return {
        'financial_info': finacial_info,
        'sec_filings': sec_filings
    }

company_research_tools = [company_research_tool]
company_rearch_agent = create_react_agent(
    llm, tools=company_research_tools, state_modifier='Yoy are a company researcher. Provide facts only not opinions'
)


def company_research_node(state: MessagesState) -> Command[Literal["supervisor"]]:
    result = company_rearch_agent.invoke(state)
    # print(f'company_research_node: {result})
    return Command(
        update = {'messages': [HumanMessage(content=result['messages'][-1].content, name='company_research')]},
        goto='supervisor'
    )


analyst_prompt = PromptTemplate.from_template(
    """You are a stock market analyst. Given the following information,
Please make a decision so that I can know clearly whether to buy, sell, or hold the stock.
After your analysis, translate your final answer into Korean.
Information:
{messages}

Translation into Korean:
{{Korean_Result}}"""
)

analyst_chain = analyst_prompt | llm

def analyst_node(state: MessagesState):
    """
    분석가 node입니다. 주어진 State를 기반으로 분석가 체인을 호출하고,
    결과 메시지를 반환합니다.

    Args:
        state (MessagesState): 현재 메시지 상태를 나타내는 객체입니다.

    Returns:
        dict: 분석 결과 메시지를 포함하는 딕셔너리를 반환합니다.
    """
    result = analyst_chain.invoke({'messages': state['messages'][1:]})

    return {'messages': [result]}


members = ["market_research", "stock_research", "company_research"]
# options = members + ["FINISH"]

system_prompt = (
    "You are a supervisor tasked with managing a conversation between the"
    f" following workers: {members}. Given the following user request," 
    " respond with the worker to act next. Each worker will perform a"
    " task and respond with their results and status. When finished,"
    " respond with FINISH."
)


class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal[members + ["FINISH"]]


def supervisor_node(state: MessagesState) -> Command[Literal[["market_research", "stock_research", "company_research"], "analyst"]]:
    """
    supervisor node입니다. 주어진 State를 기반으로 각 worker의 결과를 종합하고,
    다음에 수행할 worker를 결정합니다. 모든 작업이 완료되면 analyst node로 이동합니다.

    Args:
        state (MessagesState): 현재 메시지 상태를 나타내는 객체입니다.

    Returns:
        Command: 다음에 수행할 worker 또는 analyst node로 이동하기 위한 명령을 반환합니다.
    """
    messages = [
        {"role": "system", "content": system_prompt},
    ] + state["messages"]
    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]
    if goto == "FINISH":
        goto = "analyst"

    return Command(goto=goto)

graph_builder = StateGraph(MessagesState)

graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("market_research", market_research_node)
graph_builder.add_node("stock_research", stock_research_node)
graph_builder.add_node("company_research", company_research_node)
graph_builder.add_node("analyst", analyst_node)

graph_builder.add_edge(START, "supervisor")
graph_builder.add_edge("analyst", END)
graph = graph_builder.compile()

for chunk in graph.stream(
    {"messages": [("user", "Yould you invest in Recursion Pharmaceuticals Inc?")]}, stream_mode="values"
):
    chunk['messages'][-1].pretty_print()
