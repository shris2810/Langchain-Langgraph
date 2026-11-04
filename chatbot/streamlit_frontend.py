import streamlit as st
from langgraph_backend import chatbot, retrieve_all_threads
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid

# utility functions

def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get('messages', [])

def extract_AIMessage(message):
    if isinstance(message, AIMessage):
        # 1. Safely check if content exists and is a list
        if hasattr(message, 'content') and isinstance(message.content, list):
            if len(message.content) > 0 and 'text' in message.content[0]:
                return message.content[0]['text']
        
        # 2. Fallback if the content is just a plain string (depending on the model setup)
        if hasattr(message, 'content') and isinstance(message.content, str):
            if message.content:
                return message.content
    


# Session Setup

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

add_thread(st.session_state['thread_id'])



# Sidebar UI 

st.sidebar.title("LangGraph Chatbot")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")

for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role='user'
                msg_content = msg.content
            elif isinstance(msg, AIMessage):
                role='assistant'
                msg_content = extract_AIMessage(msg)
            
            # there will be tool messages bbut we skiped to show 
            if msg_content:
                temp_messages.append({'role': role, 'content': msg_content})

        st.session_state['message_history'] = temp_messages



# Main UI

# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.markdown(message['content'])


user_input = st.chat_input('Type here')

if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    # response = chatbot.invoke({'messages': [HumanMessage(content=user_input)]}, config=CONFIG) # type: ignore
    # ai_message = response['messages'][-1].content[0]['text']

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    with st.chat_message('assistant'):

        status_holder = {"box": None}

        # streaming response of ai
        def parse_stream():
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            ):
                # Lazily create & update the SAME status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"🔧 Using `{tool_name}` …", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"🔧 Using `{tool_name}` …",
                            state="running",
                            expanded=True,
                        )

                
                # Stream ONLY assistant tokens
                if isinstance(message_chunk, AIMessage):
                    # 1. Safely check if content exists and is a list
                    if hasattr(message_chunk, 'content') and isinstance(message_chunk.content, list):
                        if len(message_chunk.content) > 0 and 'text' in message_chunk.content[0]:
                            yield message_chunk.content[0]['text']
                    
                    # 2. Fallback if the content is just a plain string (depending on the model setup)
                    elif hasattr(message_chunk, 'content') and isinstance(message_chunk.content, str):
                        if message_chunk.content:
                            yield message_chunk.content

        # Stream the safe text fragments directly to the UI
        ai_message = st.write_stream(parse_stream())

        # Finalize only if a tool was actually used
        if status_holder["box"] is not None:
            status_holder["box"].update(
                label="✅ Tool finished", state="complete", expanded=False
            )
        
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})