import asyncio
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

agent = AzureOpenAIChatClient(
    credential=DefaultAzureCredential()
).create_agent(
    instructions="You are good at telling jokes.",
    name="Joker"
)

async def main():
    result = await agent.run("Tell me a joke about a pirate.")
    print(result.text)

asyncio.run(main())