"""System prompts for Claude adapted by audience and level."""

from src.prompts import scenarios_students, scenarios_adults

AUDIENCE_CONTEXT = {
    "students": {
        "description": "a friendly tutor helping young students learn English",
        "tone": "casual, encouraging, relatable to student life",
        "constraints": "Use simple vocabulary for lower levels, progressively more complex for higher levels"
    },
    "adults": {
        "description": "a professional English coach for working adults",
        "tone": "professional yet approachable, business-ready",
        "constraints": "Balance professional language with natural conversation flow"
    }
}

LEVEL_ADJUSTMENTS = {
    "A1": "Keep it VERY simple. Use short sentences. Focus on basic vocabulary and present tense.",
    "A2": "Use simple present and past tense. Introduce some common phrases.",
    "B1": "Use variety of tenses. Include idioms occasionally. Ask more complex questions.",
    "B2": "Use sophisticated vocabulary and complex grammar. Discuss nuanced topics.",
    "C1": "Use advanced vocabulary, idiomatic expressions, and complex structures. Challenge the user.",
    "C2": "Use native-like fluency. Discuss complex ideas. Use subtle humor and cultural references."
}


def get_system_prompt(audience: str, scenario: str, level: str) -> str:
    """Build system prompt based on audience, scenario, and level.

    Args:
        audience: 'students' or 'adults'
        scenario: scenario name (e.g., 'exams', 'job_interview')
        level: proficiency level (A1-C2)

    Returns:
        Complete system prompt for Claude
    """
    scenarios_module = scenarios_students if audience == "students" else scenarios_adults
    base_prompt = scenarios_module.get_system_prompt(scenario, level)

    audience_desc = AUDIENCE_CONTEXT.get(audience, {})
    level_adjustment = LEVEL_ADJUSTMENTS.get(level, "")

    enhanced_prompt = f"""{base_prompt}

AUDIENCE CONTEXT: You are {audience_desc.get('description', '')}.
TONE: {audience_desc.get('tone', '')}
LEVEL ADAPTATION: {level_adjustment}

Remember:
- Keep responses natural and conversational
- Gently correct errors without interrupting flow
- Provide encouragement and positive feedback
- Never switch to Russian
- Maintain the scenario context throughout"""

    return enhanced_prompt


def get_scenario_opener(audience: str, scenario: str) -> str:
    """Get opening message for a scenario.

    Args:
        audience: 'students' or 'adults'
        scenario: scenario name

    Returns:
        Opening message to start the conversation
    """
    scenarios_module = scenarios_students if audience == "students" else scenarios_adults
    return scenarios_module.get_scenario_opener(scenario)
