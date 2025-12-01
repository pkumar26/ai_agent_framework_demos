from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential

# Create client and agent
client = AzureOpenAIChatClient(
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
)

agent = client.create_agent(
    instructions="You are good at telling jokes.",
    name="Joker"
)

async def main():
    # Create a thread for persistent conversation using get_new_thread()
    thread = agent.get_new_thread()
    
    # First message
    response1 = await agent.run("My name is John.", thread=thread)
    print(f"Agent: {response1.text}\n")
    
    # Second message - agent should remember the name
    response2 = await agent.run("What's my name?", thread=thread)
    print(f"Agent: {response2.text}\n")
    
    # Third message
    response3 = await agent.run("Tell me a joke about a pirate.", thread=thread)
    print(f"Agent: {response3.text}\n")


async def interactive_chat():
    # Create a thread for the conversation
    thread = agent.get_new_thread()
    
    print("Chat with the agent (type 'quit' to exit):")
    print()
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("\nGoodbye!")
            break
            
        if user_input.strip():
            response = await agent.run(user_input, thread=thread)
            print(f"Agent: {response.text}\n")

# asyncio.run(main())
asyncio.run(interactive_chat())