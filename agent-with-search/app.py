import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import nest_asyncio

# Apply nest_asyncio to fix asyncio issues in Streamlit
nest_asyncio.apply()

load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential
from mem0 import MemoryClient

# Import your AzureAISearchKnowledgeBase class
# Option 1: If it's in documentai.py in the same folder
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from documentai import AzureAISearchKnowledgeBase
except ImportError:
    st.error("Cannot import AzureAISearchKnowledgeBase. Make sure documentai.py is in the same folder as app.py")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="AI Agent with Memory & Documents",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

if not st.session_state.initialized:
    try:
        # Create clients
        st.session_state.client = AzureOpenAIChatClient(
            credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
        )
        
        st.session_state.mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))
        
        st.session_state.knowledge_base = AzureAISearchKnowledgeBase(
            search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            search_key=os.getenv("AZURE_SEARCH_KEY"),
            index_name="documents-index"
        )
        
        st.session_state.agent = st.session_state.client.create_agent(
            instructions="You are a helpful assistant that can answer questions based on uploaded documents and remember user information.",
            name="DocumentBot"
        )
        
        st.session_state.thread = st.session_state.agent.get_new_thread()
        st.session_state.messages = []
        st.session_state.user_id = "default_user"
        st.session_state.initialized = True
        
    except Exception as e:
        st.error(f"Initialization error: {e}")
        st.stop()

# Sidebar
with st.sidebar:
    st.title("🤖 AI Agent Settings")
    
    # User ID
    st.subheader("👤 User Identity")
    new_user_id = st.text_input("User ID", value=st.session_state.user_id, key="user_id_input")
    
    if st.button("Switch User"):
        if new_user_id != st.session_state.user_id:
            st.session_state.user_id = new_user_id
            st.session_state.messages = []
            st.session_state.thread = st.session_state.agent.get_new_thread()
            st.success(f"✅ Switched to: {new_user_id}")
            st.rerun()
    
    st.divider()
    
    # Document Upload
    st.subheader("📄 Upload Documents")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'docx', 'txt', 'csv', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'],
        help="Supported: PDF, DOCX, TXT, CSV, XLSX, PNG, JPG"
    )

    if uploaded_file is not None:
        # Add sharing options
        col1, col2 = st.columns(2)
        with col1:
            is_shared = st.checkbox("🌐 Share with all users", value=False)
        with col2:
            if not is_shared:
                share_with = st.text_input(
                    "Share with users", 
                    placeholder="alice,bob,charlie",
                    help="Comma-separated user IDs"
                )
        
        if st.button("📤 Upload Document"):
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                try:
                    temp_dir = "/tmp" if os.path.exists("/tmp") else "."
                    temp_path = os.path.join(temp_dir, uploaded_file.name)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Parse allowed users
                    allowed_users = []
                    if not is_shared and share_with:
                        allowed_users = [u.strip() for u in share_with.split(",") if u.strip()]
                    
                    # Upload with access control
                    success = st.session_state.knowledge_base.upload_document(
                        temp_path,
                        user_id=st.session_state.user_id,
                        is_shared=is_shared,
                        allowed_users=allowed_users
                    )
                    
                    if success:
                        access_msg = "shared with all" if is_shared else "private"
                        if allowed_users:
                            access_msg = f"shared with: {', '.join(allowed_users)}"
                        st.success(f"✅ Uploaded: {uploaded_file.name} ({access_msg})")
                    else:
                        st.error(f"❌ Failed to upload")
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
                except Exception as e:
                    st.error(f"Upload error: {e}")
    
    st.divider()
    
    # View Documents
    st.subheader("📚 My Documents")

    if st.button("🔄 Refresh List"):
        st.rerun()

    try:
        docs = st.session_state.knowledge_base.get_all_documents(
            user_id=st.session_state.user_id,
            include_shared=True
        )
        
        if docs:
            for idx, doc in enumerate(docs, 1):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # Show document name with ownership indicator
                        if doc["owner"] == st.session_state.user_id:
                            st.text(f"📄 {doc['name']}")
                        else:
                            st.text(f"🔗 {doc['name']}")
                    
                    with col2:
                        # Show access level
                        if doc["is_shared"]:
                            st.caption("🌐 Public")
                        elif doc["owner"] == st.session_state.user_id:
                            st.caption("🔒 Private")
                        else:
                            st.caption("👥 Shared with you")
                    
                    with col3:
                        # Only show delete if user owns it
                        if doc["owner"] == st.session_state.user_id:
                            if st.button("🗑️", key=f"delete_{doc['name']}_{idx}"):
                                st.session_state.knowledge_base.delete_document(
                                    doc['name'],
                                    user_id=st.session_state.user_id
                                )
                                st.success(f"Deleted: {doc['name']}")
                                st.rerun()
        else:
            st.info("No documents available")
            
    except Exception as e:
        st.error(f"Error loading documents: {e}")
    
    st.divider()
    
    # View Memories
    st.subheader("🧠 User Memories")
    if st.button("👁️ View Memories"):
        try:
            memories = st.session_state.mem0_client.search(
                query="user information preferences facts",
                filters={"user_id": st.session_state.user_id},
                limit=50
            )
            if memories and 'results' in memories and memories['results']:
                st.write("**Stored Memories:**")
                for mem in memories['results']:
                    st.text(f"• {mem.get('memory', 'N/A')}")
            else:
                st.info("No memories stored yet")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.divider()
    
    # Clear Chat
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.session_state.thread = st.session_state.agent.get_new_thread()
        st.rerun()

# Main chat interface
st.title("💬 Chat with AI Agent")
st.caption(f"Currently chatting as: **{st.session_state.user_id}**")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Search documents
                doc_context = ""
                relevant_docs = st.session_state.knowledge_base.search(
                    prompt, 
                    top_k=5, 
                    user_id=st.session_state.user_id
                )
                if relevant_docs:
                    doc_context = "📄 Relevant information from documents:\n\n"
                    st.info(f"🔍 Found {len(relevant_docs)} relevant document chunks")
                    for doc in relevant_docs:
                        score_info = f" (score: {doc.get('score', 'N/A')}"
                        if doc.get('reranker_score'):
                            score_info += f", semantic: {doc.get('reranker_score', 'N/A')}"
                        score_info += ")"
                        st.caption(f"📄 {doc['document_name']}{score_info}")
                        doc_context += f"[From {doc['document_name']}]:\n{doc['content'][:1500]}\n\n"
                
                # Search memories
                memory_context = ""
                try:
                    relevant_memories = st.session_state.mem0_client.search(
                        query=prompt,
                        filters={"user_id": st.session_state.user_id},
                        limit=5
                    )
                    
                    if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                        memory_context = "🧠 What I remember about you:\n"
                        for mem in relevant_memories['results']:
                            memory_context += f"- {mem.get('memory', '')}\n"
                        memory_context += "\n"
                except Exception as e:
                    st.warning(f"Memory search issue: {e}")
                
                # Combine contexts
                full_context = f"{memory_context}{doc_context}\nUser question: {prompt}"
                
                # Get response synchronously (Streamlit compatible)
                async def get_response():
                    response_text = ""
                    async for chunk in st.session_state.agent.run_stream(
                        full_context, 
                        thread=st.session_state.thread
                    ):
                        if chunk.text:
                            response_text += chunk.text
                    return response_text
                
                # Run async function with nest_asyncio
                loop = asyncio.get_event_loop()
                full_response = loop.run_until_complete(get_response())
                
                # Display response
                st.markdown(full_response)
                
                # Save to memory
                try:
                    messages = [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": full_response}
                    ]
                    st.session_state.mem0_client.add(messages, user_id=st.session_state.user_id)
                except Exception as e:
                    st.warning(f"Failed to save to memory: {e}")
                
                # Add assistant response to chat
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"Error generating response: {e}")
                import traceback
                st.code(traceback.format_exc())