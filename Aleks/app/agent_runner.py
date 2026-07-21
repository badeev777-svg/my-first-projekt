# app/agent_runner.py
import os
import uuid
from collections.abc import Awaitable, Callable

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    TextBlock,
    ToolPermissionContext,
    query,
)

from app.confirmation import ConfirmationBridge
from app.risk import is_risky

SendConfirmationPrompt = Callable[[str, str, dict], Awaitable[None]]
OnText = Callable[[str], Awaitable[None]]
OnConfirmationTimeout = Callable[[], Awaitable[None]]

# Env vars to blank out of the Claude Code CLI subprocess (and therefore
# out of any Bash tool call the agent makes -- its output streams straight
# into the Telegram chat via on_text).
#
# IMPORTANT: the installed SDK's SubprocessCLITransport builds the child
# env as {**inherited_env, ..., **options.env} where inherited_env is a
# full *independent copy* of *this* process's real os.environ. That means
# merely omitting a key from options.env is a no-op -- the real value
# still flows through from inherited_env unchanged. The only way to
# actually remove a key from the child's env is to override it in
# options.env with a replacement value (here, an empty string), so it wins
# the later `**options.env` spread.
#
# ANTHROPIC_API_KEY is deliberately NOT in this set. That same CLI
# subprocess is what authenticates to the Anthropic API using
# ANTHROPIC_API_KEY, and this deployment has no other credential
# configured (see app/main.py). Blanking it here would break the bot
# entirely, so it cannot be scrubbed without a larger change (e.g. never
# exporting it into this process's os.environ at all).
_SUBPROCESS_ENV_OVERRIDES = {"TELEGRAM_BOT_TOKEN": ""}


def _subprocess_env() -> dict[str, str]:
    return {**os.environ, **_SUBPROCESS_ENV_OVERRIDES}


def make_can_use_tool(
    confirmation_bridge: ConfirmationBridge,
    send_confirmation_prompt: SendConfirmationPrompt,
    on_confirmation_timeout: OnConfirmationTimeout | None = None,
):
    async def can_use_tool(
        tool_name: str, input_data: dict, context: ToolPermissionContext
    ) -> PermissionResultAllow | PermissionResultDeny:
        if not is_risky(tool_name, input_data):
            return PermissionResultAllow(updated_input=input_data)

        correlation_id = context.tool_use_id or str(uuid.uuid4())
        timed_out = False

        async def _send(correlation_id: str) -> None:
            await send_confirmation_prompt(correlation_id, tool_name, input_data)

        async def _on_timeout(correlation_id: str) -> None:
            nonlocal timed_out
            timed_out = True
            if on_confirmation_timeout is not None:
                await on_confirmation_timeout()

        approved = await confirmation_bridge.request(correlation_id, _send, _on_timeout)
        if approved:
            return PermissionResultAllow(updated_input=input_data)
        if timed_out:
            return PermissionResultDeny(
                message="Действие отменено по таймауту ожидания подтверждения"
            )
        return PermissionResultDeny(message="Отклонено пользователем в Telegram")

    return can_use_tool


async def run_turn(
    prompt: str,
    project_path: str,
    session_id: str | None,
    confirmation_bridge: ConfirmationBridge,
    send_confirmation_prompt: SendConfirmationPrompt,
    on_text: OnText,
    on_confirmation_timeout: OnConfirmationTimeout | None = None,
) -> str | None:
    """Runs exactly one query() turn against a project and returns the
    session_id to persist for the next call's resume=."""
    options = ClaudeAgentOptions(
        cwd=project_path,
        resume=session_id,
        system_prompt={"type": "preset", "preset": "claude_code"},
        can_use_tool=make_can_use_tool(
            confirmation_bridge, send_confirmation_prompt, on_confirmation_timeout
        ),
        # Never load on-disk .claude/settings*.json from the target project.
        # If unset, the SDK loads those files and skips can_use_tool entirely
        # for tool calls already permitted by a permissions.allow rule there
        # -- silently bypassing Telegram confirmation. can_use_tool must be
        # the sole gate for every tool call, always.
        setting_sources=[],
        env=_subprocess_env(),
    )

    new_session_id: str | None = session_id
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    await on_text(block.text)
        elif isinstance(message, ResultMessage):
            new_session_id = message.session_id
    return new_session_id
