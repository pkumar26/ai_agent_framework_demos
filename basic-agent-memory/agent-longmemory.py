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

async def chat_with_mem0(user_id: str = "user_john_123"):
    """Chat with agent using Mem0 for memory"""
    thread = agent.get_new_thread()
    
    print(f"Chat with MemoryBot (User ID: {user_id})")
    print("I will remember information you share with me!")
    print("Type 'memories' to see what I remember")
    print("Type 'quit' to exit\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nGoodbye! I've saved what we discussed.")
            break
        
        if user_input.lower() == 'memories':
            # Get all memories for this user with proper filters
            try:
                memories = mem0_client.search(
                    query="",  # Empty query
                    filters={"user_id": user_id},  # Required filters parameter!
                    limit=50
                )
                print("\n=== Your Memories ===")
                if memories and 'results' in memories and memories['results']:
                    for mem in memories['results']:
                        print(f"- {mem.get('memory', 'N/A')}")
                else:
                    print("No memories found.")
            except Exception as e:
                print(f"Could not retrieve memories: {e}")
            print()
            continue
            
        if user_input.strip():
            # Search for relevant memories with proper filters
            memory_context = ""
            try:
                relevant_memories = mem0_client.search(
                    query=user_input,
                    filters={"user_id": user_id},  # Required!
                    limit=5
                )
                
                # Format memories for context
                if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                    memory_context = "What I remember about you:\n"
                    for mem in relevant_memories['results']:
                        memory_context += f"- {mem.get('memory', '')}\n"
                    memory_context += "\n"
            except Exception as e:
                print(f"[Debug] Memory search failed: {e}")
            
            # Create enhanced prompt with memory
            if memory_context:
                enhanced_prompt = f"{memory_context}User: {user_input}"
            else:
                enhanced_prompt = user_input
            
            print("Agent: ", end="", flush=True)
            
            full_response = ""
            async for chunk in agent.run_stream(enhanced_prompt, thread=thread):
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
            
            print("\n")
            
            # Add the conversation to Mem0
            try:
                messages = [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": full_response}
                ]
                mem0_client.add(messages, user_id=user_id)
            except Exception as e:
                print(f"[Debug] Failed to save memory: {e}")

async def demo_mem0_integration():
    """Demo showing Mem0 integration"""
    user_id = "user_john_123"
    thread = agent.get_new_thread()
    
    print("=== SESSION 1: Learning about you ===\n")
    
    messages_to_learn = [
        "My name is John and I love pizza.",
        "I work as a software engineer at Microsoft.",
        "My favorite programming language is Python."
    ]
    
    for user_msg in messages_to_learn:
        print(f"You: {user_msg}")
        
        # Get relevant memories with proper filters
        memory_context = ""
        try:
            relevant_memories = mem0_client.search(
                query=user_msg,
                filters={"user_id": user_id},  # Required!
                limit=3
            )
            
            # Format memory context
            if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                memory_context = "What I remember:\n"
                for mem in relevant_memories['results']:
                    memory_context += f"- {mem.get('memory', '')}\n"
                memory_context += "\n"
        except Exception as e:
            print(f"[Debug] Memory retrieval issue: {e}")
        
        enhanced_prompt = f"{memory_context}User: {user_msg}" if memory_context else user_msg
        response = await agent.run(enhanced_prompt, thread=thread)
        print(f"Agent: {response.text}\n")
        
        # Store in Mem0
        try:
            messages = [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": response.text}
            ]
            result = mem0_client.add(messages, user_id=user_id)
            print(f"[Debug] Memory saved successfully\n")
        except Exception as e:
            print(f"[Debug] Failed to save: {e}\n")
    
    print("=" * 60)
    print("=== SESSION 2: Testing memory recall ===\n")
    
    # New thread to simulate new session
    thread2 = agent.get_new_thread()
    
    questions = [
        "What do you know about me?",
        "What food should I order for dinner?",
        "What programming language do I prefer?"
    ]
    
    for question in questions:
        print(f"You: {question}")
        
        # Search memories with filters
        memory_context = ""
        try:
            relevant_memories = mem0_client.search(
                query=question,
                filters={"user_id": user_id},  # Required!
                limit=10
            )
            
            if relevant_memories and 'results' in relevant_memories and relevant_memories['results']:
                memory_context = "What I remember about you:\n"
                for mem in relevant_memories['results']:
                    memory_context += f"- {mem.get('memory', '')}\n"
                memory_context += "\n"
        except Exception as e:
            print(f"[Debug] Search failed: {e}")
        
        enhanced_prompt = f"{memory_context}User: {question}" if memory_context else question
        response = await agent.run(enhanced_prompt, thread=thread2)
        print(f"Agent: {response.text}\n")

# Choose which to run:
#asyncio.run(demo_mem0_integration())
asyncio.run(chat_with_mem0())