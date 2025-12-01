import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Page config
st.set_page_config(
    page_title="AI Agent",
    page_icon="🤖",
    layout="wide"
)

# Sidebar
with st.sidebar:
    st.title("🤖 Settings")
    st.text_input("User ID", value="john")
    st.button("Upload Document")

# Main area
st.title("💬 Chat")
st.write("Type a message below")

# Check if imports work
try:
    from agent_framework.azure import AzureOpenAIChatClient
    st.success("✅ Agent Framework imported")
except Exception as e:
    st.error(f"❌ Agent Framework error: {e}")

try:
    from mem0 import MemoryClient
    st.success("✅ Mem0 imported")
except Exception as e:
    st.error(f"❌ Mem0 error: {e}")

try:
    from azure.search.documents import SearchClient
    st.success("✅ Azure Search imported")
except Exception as e:
    st.error(f"❌ Azure Search error: {e}")

# Test .env variables
st.write("**Environment Variables:**")
st.write(f"- AZURE_OPENAI_API_KEY: {'✅ Set' if os.getenv('AZURE_OPENAI_API_KEY') else '❌ Missing'}")
st.write(f"- AZURE_SEARCH_ENDPOINT: {'✅ Set' if os.getenv('AZURE_SEARCH_ENDPOINT') else '❌ Missing'}")
st.write(f"- MEM0_API_KEY: {'✅ Set' if os.getenv('MEM0_API_KEY') else '❌ Missing'}")