import streamlit as st
import requests
import json
from datetime import datetime
import os

API_BASE_URL = "http://0.0.0.0:8000/api/v1"
HEADERS = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

SAVE_FILE = "saved_chats.json"
st.set_page_config(layout="wide")
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def load_saved_chats():
    """Load saved chats from file"""
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_chat_to_file():
    """Save current chat to file"""
    if not st.session_state.conversation_id or not st.session_state.messages:
        return
    
    saved_chats = load_saved_chats()
    saved_chats[st.session_state.conversation_id] = {
        "timestamp": datetime.now().isoformat(),
        "messages": st.session_state.messages
    }
    with open(SAVE_FILE, 'w') as f:
        json.dump(saved_chats, f, indent=2)

def load_chat(conversation_id):
    """Load a specific chat into current session"""
    saved_chats = load_saved_chats()
    if conversation_id in saved_chats:
        st.session_state.conversation_id = conversation_id
        st.session_state.messages = saved_chats[conversation_id]["messages"]

def start_new_conversation():
    """Start a new conversation with the API"""
    with st.spinner("Starting new conversation..."):
        payload = {
            "initial_message": "--",
            "language": "en-US",
            "location": {
                "latitude": 0,
                "longitude": 0,
                "country": "Unknown",
                "city": "Unknown"
            },
            "timezone": "UTC"
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/new/start",
                headers=HEADERS,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            st.session_state.conversation_id = data["conversation_id"]
            st.session_state.messages = [{
                "role": "assistant",
                "content": data["response"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }]
        except requests.exceptions.RequestException as e:
            st.error(f"Error starting conversation: {str(e)}")
            return False
    return True

def send_message(message):
    """Send a message to an existing conversation"""
    if not st.session_state.conversation_id:
        st.error("Please start a new conversation first!")
        return
    
    with st.spinner("Processing your message..."):
        payload = {
            "message": message,
            "conversation_id": st.session_state.conversation_id
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/new/chat",
                headers=HEADERS,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            st.session_state.messages.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            st.session_state.messages.append({
                "role": "assistant",
                "content": data["response"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
        except requests.exceptions.RequestException as e:
            st.error(f"Error sending message: {str(e)}")

def download_chat():
    """Generate and download chat log as txt file"""
    if not st.session_state.messages:
        st.warning("No chat history to download!")
        return
    
    chat_log = "Chat Log\n" + "="*50 + "\n\n"
    for message in st.session_state.messages:
        chat_log += f"[{message['timestamp']}] {message['role'].capitalize()}: {message['content']}\n\n"
    
    return chat_log

st.title("Flynas")

with st.sidebar:
    st.header("Controls")
    
    if st.button("New Chat"):
        st.session_state.messages = []
        start_new_conversation()
    
    if st.button("Save Chat") and st.session_state.conversation_id:
        save_chat_to_file()
        st.success("Chat saved!")
    
    if st.button("Download Chat") and st.session_state.messages:
        chat_log = download_chat()
        st.download_button(
            label="Download",
            data=chat_log,
            file_name=f"chat_{st.session_state.conversation_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    
    if st.session_state.conversation_id:
        st.write(f"Current ID: {st.session_state.conversation_id[:8]}...")
    
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
    
    st.subheader("Saved Chats")
    saved_chats = load_saved_chats()
    if saved_chats:
        for conv_id, chat_data in saved_chats.items():
            if st.button(f"{conv_id[:8]}... ({chat_data['timestamp'][:10]})"):
                load_chat(conv_id)
                st.rerun()
    else:
        st.write("No saved chats yet")

chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(f"**{message['timestamp']}**: {message['content']}")

if st.session_state.conversation_id:
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Type your message here...", key="user_input")
        submit_button = st.form_submit_button(label="Send")
        
        if submit_button and user_input:
            send_message(user_input)
            st.rerun()
else:
    st.info("Please start a new conversation using the button in the sidebar.")

st.markdown("""
    <style>
    .stChatMessage {
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #DCF8C6;
        padding: 10px;
        border-radius: 5px;
    }
    .assistant-message {
        background-color: #ECECEC;
        padding: 10px;
        border-radius: 5px;
    }
    .stButton>button {
        width: 100%;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)