from dotenv import load_dotenv
import os
import asyncio
import json
from typing import Dict, List

load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential

# Create client
client = AzureOpenAIChatClient(
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
)

# Simple memory storage
class SimpleMemory:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memories: Dict[str, any] = {}
        self.conversation_history: List[str] = []
    
    def add_fact(self, key: str, value: any):
        """Store a fact about the user"""
        self.memories[key] = value
    
    def get_fact(self, key: str):
        """Retrieve a fact about the user"""
        return self.memories.get(key)
    
    def get_all_memories(self) -> str:
        """Get all memories as a formatted string"""
        if not self.memories:
            return "No memories stored yet."
        
        memory_str = "What I know about you:\n"
        for key, value in self.memories.items():
            memory_str += f"- {key}: {value}\n"
        return memory_str
    
    def add_to_history(self, message: str):
        """Add to conversation history"""
        self.conversation_history.append(message)
    
    def extract_info_from_message(self, message: str):
        """Simple extraction of common patterns"""
        message_lower = message.lower()
        
        # Extract name
        if "my name is" in message_lower:
            words = message.split()
            try:
                name_idx = words.index("is") + 1
                if name_idx < len(words):
                    name = words[name_idx].strip(".,!?")
                    self.add_fact("name", name)
            except:
                pass
        
        # Extract job
        if "i work as" in message_lower or "i am a" in message_lower:
            if "work as" in message_lower:
                job_start = message_lower.index("work as") + 8
            elif "i am a" in message_lower:
                job_start = message_lower.index("i am a") + 6
            
            job_text = message[job_start:].split('.')[0].split(',')[0].strip()
            if job_text:
                self.add_fact("job", job_text)
        
        # Extract favorites
        if "i love" in message_lower or "my favorite" in message_lower:
            if "i love" in message_lower:
                fav_start = message_lower.index("i love") + 7
                fav_text = message[fav_start:].split('.')[0].split(',')[0].strip()
                self.add_fact("loves", fav_text)
            
            if "my favorite" in message_lower:
                fav_start = message_lower.index("my favorite") + 12
                # Get the category (e.g., "programming language")
                rest = message[fav_start:].split(' is ')
                if len(rest) >= 2:
                    category = rest[0].strip()
                    value = rest[1].split('.')[0].split(',')[0].strip()
                    self.add_fact(f"favorite_{category.replace(' ', '_')}", value)

# Create memory instance
user_memory = SimpleMemory("user_john_123")

# Create agent with enhanced instructions
agent = client.create_agent(
    instructions="""You are a helpful personal assistant. 
    When users share personal information with you (name, job, preferences, etc.), 
    acknowledge that you'll remember it.
    When asked what you know about them, reference the specific information they've shared.""",
    name="MemoryBot"
)

async def chat_with_memory(memory: SimpleMemory):
    """Chat function that uses simple memory"""
    thread = agent.get_new_thread()
    
    print(f"Chat with MemoryBot (User ID: {memory.user_id})")
    print("I will remember information you share with me!")
    print("Type 'memories' to see what I remember")
    print("Type 'quit' to exit\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nGoodbye! I've saved what we discussed.")
            break
        
        if user_input.lower() == 'memories':
            print(f"\n{memory.get_all_memories()}\n")
            continue
            
        if user_input.strip():
            # Extract information from user message
            memory.extract_info_from_message(user_input)
            memory.add_to_history(f"User: {user_input}")
            
            # Add memory context to the message
            memory_context = memory.get_all_memories()
            enhanced_prompt = f"{memory_context}\n\nUser says: {user_input}"
            
            print("Agent: ", end="", flush=True)
            
            full_response = ""
            async for chunk in agent.run_stream(enhanced_prompt, thread=thread):
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
            
            memory.add_to_history(f"Agent: {full_response}")
            print("\n")

async def demo_simple_memory():
    """Demo showing memory across different conversation topics"""
    memory = SimpleMemory("user_john_123")
    thread = agent.get_new_thread()
    
    print("=== SESSION 1: Learning about you ===\n")
    
    # First conversation
    messages = [
        "My name is John and I love pizza.",
        "I work as a software engineer at Microsoft.",
        "My favorite programming language is Python."
    ]
    
    for msg in messages:
        print(f"You: {msg}")
        memory.extract_info_from_message(msg)
        memory_context = memory.get_all_memories()
        enhanced_prompt = f"{memory_context}\n\nUser says: {msg}"
        
        response = await agent.run(enhanced_prompt, thread=thread)
        print(f"Agent: {response.text}\n")
    
    print("=" * 60)
    print("=== Current Memories ===")
    print(memory.get_all_memories())
    print("=" * 60)
    
    # New conversation using stored memories
    print("\n=== SESSION 2: Using memories ===\n")
    
    follow_up_questions = [
        "What do you know about me?",
        "What food should I order for dinner?",
        "What job do I have?"
    ]
    
    for question in follow_up_questions:
        print(f"You: {question}")
        memory_context = memory.get_all_memories()
        enhanced_prompt = f"{memory_context}\n\nUser says: {question}"
        
        response = await agent.run(enhanced_prompt, thread=thread)
        print(f"Agent: {response.text}\n")

# Choose which to run:
asyncio.run(demo_simple_memory())
# asyncio.run(chat_with_memory(user_memory))