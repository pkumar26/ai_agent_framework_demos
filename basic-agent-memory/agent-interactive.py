from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential
from mem0 import MemoryClient

# Create Azure OpenAI client
client = AzureOpenAIChatClient(
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
)

# Create Mem0 client
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# Create agent
agent = client.create_agent(
    instructions="You are a helpful personal assistant that remembers information about the user.",
    name="MemoryBot"
)

async def interactive_multi_user_chat():
    """Interactive chat where you can switch between users"""
    
    print("=" * 70)
    print("       🤖 MULTI-USER MEMORY CHAT SYSTEM 🤖")
    print("=" * 70)
    print("\n📝 Commands:")
    print("  /switch <user_id>  - Switch to a different user")
    print("  /memories          - Show current user's memories")
    print("  /users             - Show all active users")
    print("  /clear             - Clear screen")
    print("  /quit              - Exit")
    print("\n💡 Tip: Start by entering a user ID (e.g., 'john', 'alice', 'bob')")
    print("=" * 70 + "\n")
    
    current_user_id = None
    users = {}  # Track all users and their threads
    
    while True:
        # If no user is selected, ask for one
        if current_user_id is None:
            user_input = input("👤 Enter user ID to start chatting: ").strip()
            if not user_input:
                continue
            
            if user_input.lower() == '/quit':
                print("\n👋 Goodbye!")
                break
                
            current_user_id = user_input
            if current_user_id not in users:
                users[current_user_id] = {"thread": agent.get_new_thread()}
            
            print(f"\n✅ Now chatting as: {current_user_id}")
            print(f"💬 Start talking or use commands\n")
            continue
        
        # Get user input with current user prefix
        user_input = input(f"[{current_user_id}]> ").strip()
        
        if not user_input:
            continue
        
        # Handle /switch command
        if user_input.startswith("/switch"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                new_user_id = parts[1].strip()
                if new_user_id not in users:
                    users[new_user_id] = {"thread": agent.get_new_thread()}
                current_user_id = new_user_id
                print(f"\n✅ Switched to: {current_user_id}\n")
            else:
                print("❌ Usage: /switch <user_id>\n")
            continue
        
        # Handle /memories command - FIXED VERSION
        if user_input == "/memories":
            try:
                # Use a generic query instead of empty string
                memories = mem0_client.search(
                    query="user information preferences facts",  # Non-empty query
                    filters={"user_id": current_user_id},
                    limit=50
                )
                print(f"\n{'='*70}")
                print(f"🧠 Memories for '{current_user_id}'")
                print(f"{'='*70}")
                if memories and 'results' in memories and memories['results']:
                    for idx, mem in enumerate(memories['results'], 1):
                        print(f"{idx}. {mem.get('memory', 'N/A')}")
                else:
                    print("📭 No memories found for this user yet.")
                print(f"{'='*70}\n")
            except Exception as e:
                print(f"❌ Error retrieving memories: {e}\n")
            continue
        
        # Handle /users command
        if user_input == "/users":
            print(f"\n{'='*70}")
            print(f"👥 Active Users ({len(users)} total)")
            print(f"{'='*70}")
            for user_id in users.keys():
                marker = "👉" if user_id == current_user_id else "   "
                print(f"{marker} {user_id}")
            print(f"{'='*70}\n")
            continue
        
        # Handle /clear command
        if user_input == "/clear":
            os.system('clear' if os.name != 'nt' else 'cls')
            print(f"✅ Chatting as: {current_user_id}\n")
            continue
        
        # Handle /quit command
        if user_input == "/quit":
            print("\n👋 Goodbye!")
            break
        
        # Regular chat message
        if user_input:
            # Get relevant memories
            memory_context = ""
            try:
                relevant_memories = mem0_client.search(
                    query=user_input,
                    filters={"user_id": current_user_id},
                    limit=5
                )
                
                if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                    memory_context = "What I remember about you:\n"
                    for mem in relevant_memories['results']:
                        memory_context += f"- {mem.get('memory', '')}\n"
                    memory_context += "\n"
            except Exception as e:
                print(f"[Debug] Memory search failed: {e}")
            
            # Create enhanced prompt with memory
            enhanced_prompt = f"{memory_context}User: {user_input}" if memory_context else user_input
            
            print("🤖 Agent: ", end="", flush=True)
            
            full_response = ""
            try:
                async for chunk in agent.run_stream(enhanced_prompt, thread=users[current_user_id]["thread"]):
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

# Run the interactive chat
asyncio.run(interactive_multi_user_chat())