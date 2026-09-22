import asyncio
import httpx
from src.config import Config

async def test_openrouter():
    cfg = Config()

    url = "https://openrouter.io/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": cfg.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "max_tokens": 100,
    }

    print(f"URL: {url}")
    print(f"Model: {cfg.LLM_MODEL}")
    print(f"API Key (first 30 chars): {cfg.OPENROUTER_API_KEY[:30]}...")
    print(f"\nSending request...\n")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=10)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")

            if response.status_code == 200:
                print("\n[OK] OpenRouter API is working!")
            else:
                print(f"\n[ERROR] API returned {response.status_code}")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
