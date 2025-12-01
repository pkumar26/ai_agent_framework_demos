"""
Streamlit AI Agent with Entra ID Authentication

This application provides an AI agent with document search capabilities
and Entra ID authentication for secure user access.
"""

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

# Import authentication
from entraid_auth import EntraIDAuth, StreamlitEntraIDAuth

# Import your AzureAISearchKnowledgeBase class
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from documentai import AzureAISearchKnowledgeBase
except ImportError:
    st.error("Cannot import AzureAISearchKnowledgeBase. Make sure documentai.py is in the same folder.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="AI Agent with Entra ID Auth",
    page_icon="🔐",
    layout="wide"
)

# Initialize authentication
if 'auth_initialized' not in st.session_state:
    try:
        auth = EntraIDAuth()
        st.session_state.streamlit_auth = StreamlitEntraIDAuth(auth)
        st.session_state.streamlit_auth.initialize_auth_session(st.session_state)
        st.session_state.auth_initialized = True
    except Exception as e:
        st.error(f"❌ Authentication setup error: {e}")
        st.info("Make sure ENTRA_TENANT_ID and ENTRA_CLIENT_ID are set in your .env file")
        st.stop()

# Handle OAuth callback
# Use st.query_params (new API) and convert to dict format
query_params = dict(st.query_params)
if query_params and 'code' in query_params and not st.session_state.authenticated:
    if st.session_state.streamlit_auth.handle_callback(st.session_state, query_params):
        # Clear query params after successful authentication
        st.query_params.clear()
        st.rerun()

# Show login screen if not authenticated
if not st.session_state.authenticated:
    st.title("🔐 AI Agent with Document Search")
    st.subheader("Sign in to continue")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ### Welcome!
        
        This application provides:
        - 🤖 AI-powered chat assistant
        - 📄 Document upload and search (PDF, DOCX, TXT, CSV, Excel, Images)
        - 🔒 Secure document access control
        - 🧠 Personalized memory across sessions
        
        **Please sign in with your Microsoft account to continue.**
        """)
        
        st.info("ℹ️ You'll be redirected to Microsoft login page")
        
        if st.button("🔑 Sign In with Microsoft", use_container_width=True):
            auth_url = st.session_state.streamlit_auth.start_login(st.session_state)
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
            st.write("Redirecting to Microsoft login...")
    
    st.stop()

# User is authenticated - proceed with main app

# Initialize AI components
if 'ai_initialized' not in st.session_state:
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
        
        # Use authenticated user's email/principal name as user_id to align with sharing
        st.session_state.current_user_id = (
            st.session_state.user_info.get('email')
            or st.session_state.user_info.get('preferred_username')
            or 'default_user'
        )
        
        st.session_state.ai_initialized = True
        
    except Exception as e:
        st.error(f"Initialization error: {e}")
        st.stop()

# Sidebar
with st.sidebar:
    st.title("🔐 AI Agent")
    
    # User Info
    st.subheader("👤 Signed In As")
    user_info = st.session_state.user_info
    
    with st.expander("User Profile", expanded=True):
        st.write(f"**Name:** {user_info.get('display_name', user_info.get('name', 'User'))}")
        st.write(f"**Email:** {user_info.get('email', 'N/A')}")
        if user_info.get('job_title'):
            st.write(f"**Title:** {user_info['job_title']}")
        if user_info.get('department'):
            st.write(f"**Dept:** {user_info['department']}")
        st.caption(f"User ID: {st.session_state.current_user_id[:8]}...")
    
    if st.button("🚪 Sign Out"):
        st.session_state.streamlit_auth.logout(st.session_state)
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
                    placeholder="user@domain.com",
                    help="Comma-separated email addresses"
                )
        
        if st.button("📤 Upload Document"):
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                try:
                    temp_dir = "/tmp" if os.path.exists("/tmp") else "."
                    temp_path = os.path.join(temp_dir, uploaded_file.name)
                    
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Parse allowed users (email addresses recommended)
                    allowed_users = []
                    if not is_shared and share_with:
                        allowed_users = [u.strip() for u in share_with.split(",") if u.strip()]
                    
                    # Upload with access control using authenticated user's ID
                    success = st.session_state.knowledge_base.upload_document(
                        temp_path,
                        user_id=st.session_state.current_user_id,
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
            user_id=st.session_state.current_user_id,
            include_shared=True
        )
        
        if docs:
            for idx, doc in enumerate(docs, 1):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # Show document name with ownership indicator
                        if doc["owner"] == st.session_state.current_user_id:
                            st.text(f"📄 {doc['name']}")
                        else:
                            st.text(f"🔗 {doc['name']}")
                    
                    with col2:
                        # Show access level
                        if doc["is_shared"]:
                            st.caption("🌐 Public")
                        elif doc["owner"] == st.session_state.current_user_id:
                            st.caption("🔒 Private")
                        else:
                            st.caption("👥 Shared with you")
                    
                    with col3:
                        # Only show delete if user owns it
                        if doc["owner"] == st.session_state.current_user_id:
                            if st.button("🗑️", key=f"delete_{doc['name']}_{idx}"):
                                st.session_state.knowledge_base.delete_document(
                                    doc['name'],
                                    user_id=st.session_state.current_user_id
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
                filters={"user_id": st.session_state.current_user_id},
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

# Display user info in main area
col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"Signed in as: **{user_info.get('name', 'User')}** ({user_info.get('email', '')})")
with col2:
    st.caption(f"User ID: {st.session_state.current_user_id[:16]}...")

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
                # Search documents (using authenticated user's ID)
                doc_context = ""
                relevant_docs = st.session_state.knowledge_base.search(
                    prompt, 
                    top_k=5, 
                    user_id=st.session_state.current_user_id
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
                
                # Search memories (using authenticated user's ID)
                memory_context = ""
                try:
                    relevant_memories = st.session_state.mem0_client.search(
                        query=prompt,
                        filters={"user_id": st.session_state.current_user_id},
                        limit=5
                    )
                    
                    if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                        memory_context = "🧠 What I remember about you:\n"
                        for mem in relevant_memories['results']:
                            memory_context += f"- {mem.get('memory', '')}\n"
                        memory_context += "\n"
                except Exception as e:
                    st.warning(f"Memory search issue: {e}")
                
                # Add user context to prompt
                user_context = f"User: {user_info.get('name', 'User')}"
                if user_info.get('job_title'):
                    user_context += f", {user_info['job_title']}"
                if user_info.get('department'):
                    user_context += f" at {user_info['department']}"
                user_context += "\n\n"
                
                # Combine contexts
                full_context = f"{user_context}{memory_context}{doc_context}\nUser question: {prompt}"
                
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
                
                # Save to memory (with authenticated user's ID)
                try:
                    messages = [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": full_response}
                    ]
                    st.session_state.mem0_client.add(messages, user_id=st.session_state.current_user_id)
                except Exception as e:
                    st.warning(f"Failed to save to memory: {e}")
                
                # Add assistant response to chat
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                st.error(f"Error generating response: {e}")
                import traceback
                st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.caption("🔐 Secured with Microsoft Entra ID | 🤖 Powered by Azure OpenAI")
