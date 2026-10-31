from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(), override=True)

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import sqlite3

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    temperature=0.7,
    max_retries=2,
)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set()
    for ck in checkpointer.list(None):
        all_threads.add(ck.config['configurable']['thread_id'])
    
    return list(all_threads)


#test
'''CONFIG = {'configurable': {'thread_id': 'thread1'}}

res = chatbot.invoke(
                {'messages': [HumanMessage(content='hi my name is srishti')]},
                config=CONFIG,
            )

print(res)'''