"""Smoke test: Claude Agent SDK structured output with OAuth token."""

import asyncio
import json
import subprocess

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query


def get_oauth_token() -> str:
    raw = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-s",
            "Claude Code-credentials",
            "-a",
            "silviogutierrez",
            "-w",
        ],
        capture_output=True,
        text=True,
    ).stdout.strip()
    data = json.loads(raw)
    return data["claudeAiOauth"]["accessToken"]


DRAFT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "includes_link": {"type": "boolean"},
            "skip_reason": {"type": ["string", "null"]},
            "extracted_params": {
                "type": "object",
                "properties": {
                    "peptide": {"type": ["string", "null"]},
                    "vial": {"type": ["string", "null"]},
                    "dose": {"type": ["string", "null"]},
                },
                "required": ["peptide", "vial", "dose"],
                "additionalProperties": False,
            },
        },
        "required": ["reply", "includes_link", "skip_reason", "extracted_params"],
        "additionalProperties": False,
    },
}


async def main() -> None:
    token = get_oauth_token()
    print(f"Token: {token[:25]}...")

    prompt = """You are a helpful peptide dosing assistant. Reply to this Reddit post:

Title: "How much BPC-157 should I take for a knee injury?"
Body: "I just got a 5mg vial. Not sure how much to reconstitute with or what dose to inject. Any help?"

Reply casually in 2-3 sentences. Include a calculator link:
https://www.joyapp.com/peptides/?peptide=bpc-157&vial=5&dose=250&t=TEST123

Set includes_link to true. Set skip_reason to null. Extract the peptide params from the post."""

    print("\nRunning structured output test...\n")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=[],
            model="claude-opus-4-6",
            output_format=DRAFT_SCHEMA,
            env={"CLAUDE_CODE_OAUTH_TOKEN": token},
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"Cost: ${message.total_cost_usd}")
            print(f"Is error: {message.is_error}")
            print(f"Result: {message.result}")
            print(f"Structured output: {message.structured_output}")
            if message.structured_output:
                print(f"\n--- Parsed fields ---")
                print(f"Reply: {message.structured_output.get('reply')}")
                print(f"Includes link: {message.structured_output.get('includes_link')}")
                print(f"Skip reason: {message.structured_output.get('skip_reason')}")
                print(f"Params: {message.structured_output.get('extracted_params')}")
        elif hasattr(message, "content"):
            for block in message.content:
                if hasattr(block, "text"):
                    print(f"Assistant: {block.text}")


asyncio.run(main())
