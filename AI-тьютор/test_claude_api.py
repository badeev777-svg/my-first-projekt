import asyncio
from src.services.claude import get_claude_response, get_initial_response
from src.prompts import system_prompts

async def test_initial_response():
    """Test starten message from Claude"""
    print("=" * 60)
    print("TEST 1: Initial Response (Starters message)")
    print("=" * 60)

    system_prompt = system_prompts.get_system_prompt("students", "exams", "B1")
    opener = system_prompts.get_scenario_opener("students", "exams")

    print(f"System Prompt: {system_prompt[:100]}...")
    print(f"Opener: {opener}")
    print("\nCalling Claude...")

    try:
        response = await get_initial_response(system_prompt, opener)
        print(f"\n[SUCCESS] Response: {response}\n")
        return True
    except Exception as e:
        print(f"\n[FAILED] Error: {e}\n")
        return False


async def test_dialog_response():
    """Test dialog response with history"""
    print("=" * 60)
    print("TEST 2: Dialog Response (with history)")
    print("=" * 60)

    system_prompt = system_prompts.get_system_prompt("students", "exams", "B1")

    history = [
        {"role": "assistant", "content": "Hello! I'm your English tutor. Let's discuss exam preparation strategies."},
        {"role": "user", "content": "What subjects should I focus on?"}
    ]

    user_message = "I have biology, chemistry, and physics exams"

    print(f"History: {history}")
    print(f"User: {user_message}")
    print("\nCalling Claude...")

    try:
        response = await get_claude_response(
            system_prompt=system_prompt,
            history=history,
            user_message=user_message,
            max_tokens=200
        )
        print(f"\n[SUCCESS] Response: {response}\n")
        return True
    except Exception as e:
        print(f"\n[FAILED] Error: {e}\n")
        return False


async def main():
    print("\n[TEST] Testing Claude API via OpenRouter\n")

    test1_passed = await test_initial_response()
    test2_passed = await test_dialog_response()

    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Test 1 (Initial Response): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Test 2 (Dialog Response):  {'PASSED' if test2_passed else 'FAILED'}")

    if test1_passed and test2_passed:
        print("\n[OK] All tests passed! Claude API is working correctly.")
    else:
        print("\n[ERROR] Some tests failed. Check OPENROUTER_API_KEY and API quota.")


if __name__ == "__main__":
    asyncio.run(main())
