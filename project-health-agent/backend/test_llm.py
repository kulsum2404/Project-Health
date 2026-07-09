import asyncio
from app.llm_client import get_llm_client

async def main():
    llm = get_llm_client()
    print("Sending request...")
    res = await llm.complete(system_prompt="You are a bot", user_prompt="say hello", max_tokens=10)
    print("Response:", res)

if __name__ == "__main__":
    asyncio.run(main())
