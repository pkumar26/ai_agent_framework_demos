from dotenv import load_dotenv
import os
import asyncio

# Load environment variables
load_dotenv()

from agent_framework.azure import AzureOpenAIChatClient
from azure.core.credentials import AzureKeyCredential

# Create agent with API key
agent = AzureOpenAIChatClient(
    credential=AzureKeyCredential(os.getenv("AZURE_OPENAI_API_KEY")),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
).create_agent(
    instructions="You are an personal assistant that keeps track of user's day-to-day schedule and information.",
    name="AssistantBot"
)

async def main():
    result = await agent.run("My name is John.")
    print(result.text)

    result = await agent.run("what is my name?")
    print(result.text)

asyncio.run(main())