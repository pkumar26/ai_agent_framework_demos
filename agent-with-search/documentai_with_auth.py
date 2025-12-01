"""
Command-Line AI Agent with Entra ID Authentication

This script provides an interactive CLI for the AI agent with
document search capabilities and Entra ID authentication.
"""

from dotenv import load_dotenv
import os
import asyncio
from pathlib import Path

load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential
from mem0 import MemoryClient

# Import authentication
from entraid_auth import EntraIDAuth, CLIEntraIDAuth

# Import knowledge base
from documentai import AzureAISearchKnowledgeBase

# Initialize Azure OpenAI client
client = AzureOpenAIChatClient(
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
)

# Create Mem0 client
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# Create agent
agent = client.create_agent(
    instructions="You are a helpful assistant that can answer questions based on uploaded documents and remember user information.",
    name="DocumentBot"
)

# Initialize Azure AI Search
knowledge_base = AzureAISearchKnowledgeBase(
    search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    search_key=os.getenv("AZURE_SEARCH_KEY"),
    index_name="documents-index"
)


async def authenticated_chat():
    """Main chat function with Entra ID authentication"""
    
    # Initialize authentication
    auth = EntraIDAuth()
    cli_auth = CLIEntraIDAuth(auth)
    
    # Authenticate user
    auth_result = cli_auth.authenticate_interactive()
    if not auth_result:
        print("❌ Authentication failed. Exiting.")
        return
    
    access_token = auth_result['access_token']
    user_info = auth_result['user_info']
    
    # Use email/principal name as user_id so sharing with emails matches access control
    current_user_id = (
        user_info.get('email')
        or user_info.get('preferred_username')
        or 'default_user'
    )
    
    print("=" * 70)
    print("   🤖 AZURE AI SEARCH + MEMORY CHAT SYSTEM 🤖")
    print("=" * 70)
    print(f"\n✅ Authenticated as: {user_info.get('name', 'User')}")
    print(f"📧 Email: {user_info.get('email', 'N/A')}")
    if user_info.get('job_title'):
        print(f"💼 Title: {user_info['job_title']}")
    if user_info.get('department'):
        print(f"🏢 Department: {user_info['department']}")
    print(f"\n🔑 User ID: {current_user_id[:16]}...")
    
    print("\n📝 Commands:")
    print("  /upload <file_path>        - Upload a local document")
    print("  /uploadblob <blob_url>     - Upload from Azure Blob Storage")
    print("  /share <doc_name> <users>  - Share document with users (comma-separated)")
    print("  /docs                      - List all uploaded documents")
    print("  /index                     - Show detailed index information")
    print("  /delete <doc_name>         - Delete a document from the index")
    print("  /memories                  - Show your memories")
    print("  /whoami                    - Show current user info")
    print("  /quit                      - Exit")
    print("=" * 70 + "\n")
    
    thread = agent.get_new_thread()
    
    while True:
        user_input = input(f"[{user_info.get('name', 'User')}]> ").strip()
        
        if not user_input:
            continue
        
        # Handle /upload command (LOCAL FILES)
        if user_input.startswith("/upload ") and not user_input.startswith("/uploadblob"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                file_path = parts[1].strip()
                
                if not os.path.exists(file_path):
                    print(f"❌ File not found: {file_path}\n")
                    continue
                
                knowledge_base.upload_document(file_path, user_id=current_user_id)
                print()
            else:
                print("❌ Usage: /upload <file_path>\n")
            continue
        
        # Handle /uploadblob command (AZURE BLOB FILES)
        if user_input.startswith("/uploadblob"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                blob_url = parts[1].strip()
                knowledge_base.upload_from_blob(blob_url, user_id=current_user_id)
                print()
            else:
                print("❌ Usage: /uploadblob <blob_url>\n")
                print("   Example: /uploadblob https://mystorageaccount.blob.core.windows.net/documents/file.pdf\n")
            continue
        
        # Handle /docs command
        if user_input == "/docs":
            docs = knowledge_base.get_all_documents(user_id=current_user_id, include_shared=True)
            print(f"\n{'='*70}")
            print(f"📚 Accessible Documents ({len(docs)} total)")
            print(f"{'='*70}")
            if docs:
                for idx, doc in enumerate(docs, 1):
                    access = "🌐 Public" if doc["is_shared"] else "🔒 Private"
                    owner_indicator = "👤 You" if doc["owner"] == current_user_id else f"👥 {doc['owner'][:8]}..."
                    print(f"{idx}. {doc['name']} | {access} | Owner: {owner_indicator}")
            else:
                print("No documents available.")
            print(f"{'='*70}\n")
            continue
        
        # Handle /delete command
        if user_input.startswith("/delete"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                doc_name = parts[1].strip()
                knowledge_base.delete_document(doc_name, user_id=current_user_id)
                print()
            else:
                print("❌ Usage: /delete <doc_name>\n")
            continue
        
        # Handle /share command
        if user_input.startswith("/share"):
            parts = user_input.split(maxsplit=2)
            if len(parts) >= 3:
                doc_name = parts[1].strip()
                users_str = parts[2].strip()
                target_users = [u.strip() for u in users_str.split(",") if u.strip()]
                
                if target_users:
                    knowledge_base.share_document(doc_name, current_user_id, target_users)
                    print()
                else:
                    print("❌ No valid users provided\n")
            else:
                print("❌ Usage: /share <doc_name> <user1,user2,user3>\n")
                print("   Example: /share report.pdf alice@company.com,bob@company.com\n")
            continue
        
        # Handle /memories command
        if user_input == "/memories":
            try:
                memories = mem0_client.search(
                    query="user information preferences facts",
                    filters={"user_id": current_user_id},
                    limit=50
                )
                print(f"\n{'='*70}")
                print(f"🧠 Memories for '{user_info.get('name', 'User')}'")
                print(f"{'='*70}")
                if memories and 'results' in memories and memories['results']:
                    for idx, mem in enumerate(memories['results'], 1):
                        print(f"{idx}. {mem.get('memory', 'N/A')}")
                else:
                    print("📭 No memories found.")
                print(f"{'='*70}\n")
            except Exception as e:
                print(f"❌ Error retrieving memories: {e}\n")
            continue
        
        # Handle /whoami command
        if user_input == "/whoami":
            print(f"\n{'='*70}")
            print("👤 Current User Information")
            print(f"{'='*70}")
            print(f"Name: {user_info.get('name', 'N/A')}")
            print(f"Display Name: {user_info.get('display_name', 'N/A')}")
            print(f"Email: {user_info.get('email', 'N/A')}")
            print(f"User ID: {user_info.get('user_id', 'N/A')}")
            print(f"Tenant ID: {user_info.get('tenant_id', 'N/A')}")
            if user_info.get('job_title'):
                print(f"Job Title: {user_info['job_title']}")
            if user_info.get('department'):
                print(f"Department: {user_info['department']}")
            print(f"{'='*70}\n")
            continue

        # Handle /index command
        if user_input == "/index":
            try:
                # Get ALL documents from the index
                results = knowledge_base.search_client.search(
                    search_text="*",
                    top=1000,
                    select=["id", "document_name", "chunk_id", "owner_user_id", "is_shared"]
                )
                
                # Group by document name
                docs = {}
                for result in results:
                    doc_name = result["document_name"]
                    if doc_name not in docs:
                        docs[doc_name] = {
                            "chunks": 0,
                            "owner": result.get("owner_user_id", "unknown"),
                            "is_shared": result.get("is_shared", False)
                        }
                    docs[doc_name]["chunks"] += 1
                
                print(f"\n{'='*70}")
                print(f"📊 Documents in Azure AI Search Index")
                print(f"{'='*70}")
                if docs:
                    for doc_name, info in docs.items():
                        access = "🌐 Public" if info["is_shared"] else "🔒 Private"
                        owner_display = "You" if info["owner"] == current_user_id else info["owner"][:8] + "..."
                        print(f"📄 {doc_name} ({info['chunks']} chunks) | {access} | Owner: {owner_display}")
                else:
                    print("No documents found in the index.")
                print(f"{'='*70}\n")
            except Exception as e:
                print(f"❌ Error querying index: {e}\n")
            continue

        # Handle /quit command
        if user_input == "/quit":
            print("\n👋 Goodbye!")
            break
        
        # Regular chat message - search Azure AI Search and memories
        if user_input:
            # Search Azure AI Search for relevant context
            doc_context = ""
            relevant_docs = knowledge_base.search(user_input, top_k=5, user_id=current_user_id)
            if relevant_docs:
                doc_context = "📄 Relevant information from documents:\n\n"
                print(f"[Debug] Found {len(relevant_docs)} relevant chunks")
                for idx, doc in enumerate(relevant_docs, 1):
                    print(f"[Debug] Chunk {idx}: {doc['document_name']} (score: {doc.get('score', 'N/A')})")
                    doc_context += f"[From {doc['document_name']}]:\n{doc['content'][:1500]}\n\n"
            
            # Search Mem0 for memories
            memory_context = ""
            try:
                relevant_memories = mem0_client.search(
                    query=user_input,
                    filters={"user_id": current_user_id},
                    limit=5
                )
                
                if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                    memory_context = "🧠 What I remember about you:\n"
                    for mem in relevant_memories['results']:
                        memory_context += f"- {mem.get('memory', '')}\n"
                    memory_context += "\n"
            except Exception as e:
                print(f"[Debug] Memory search failed: {e}")
            
            # Add user context
            user_context = f"User: {user_info.get('name', 'User')}"
            if user_info.get('job_title'):
                user_context += f", {user_info['job_title']}"
            if user_info.get('department'):
                user_context += f" at {user_info['department']}"
            user_context += "\n\n"
            
            # Combine contexts
            full_context = f"{user_context}{memory_context}{doc_context}\nUser question: {user_input}"
            
            print("🤖 Agent: ", end="", flush=True)
            
            full_response = ""
            try:
                async for chunk in agent.run_stream(full_context, thread=thread):
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        full_response += chunk.text
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue
            
            print("\n")
            
            # Save to Mem0
            try:
                messages = [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": full_response}
                ]
                mem0_client.add(messages, user_id=current_user_id)
            except Exception as e:
                print(f"[Debug] Failed to save memory: {e}")


# Run the authenticated chat
if __name__ == "__main__":
    asyncio.run(authenticated_chat())
