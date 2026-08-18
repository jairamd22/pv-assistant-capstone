"""Chainlit chat UI for the pharmacovigilance assistant.

Run:  chainlit run app.py --host 0.0.0.0 --port 8000
"""

import uuid
import json
import chainlit as cl
from dotenv import load_dotenv
load_dotenv()
from pv_assistant import db
from pv_assistant.agent import run_agent

DISCLAIMER = (
    "⚠️ Decision-support only — outputs cite retrieved label/regulation "
    "text and voluntary adverse-event reports (no causation implied). "
    "A human safety reviewer makes the call."
)


@cl.on_chat_start
async def start():
    await cl.Message(
        content="**Pharmacovigilance Signal & Label-Gap Assistant**\n\n"
        "Ask about adverse event reports, label coverage, or regulatory "
        "requirements — e.g. *\"We're seeing reports of respiratory "
        "depression with gabapentin — is that already reflected in the "
        "label?\"*\n\n" + DISCLAIMER
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    steps = []

    def on_tool(name, args, result):
        steps.append((name, args))

    answer_data = await cl.make_async(run_agent)(message.content, on_tool=on_tool)

    # show which tools the agent chose (the agentic upgrade, made visible)
    if steps:
        tool_lines = "\n".join(f"- `{n}` → `{a}`" for n, a in steps)
        async with cl.Step(name="Agent tool calls") as step:
            step.output = tool_lines

    conversation_id = str(uuid.uuid4())
    db.save_conversation(conversation_id, message.content, answer_data)

    actions = [
        cl.Action(name="feedback",
                  value=json.dumps({"id": conversation_id, "score": 1}),
                  label="👍 Helpful"),
        cl.Action(name="feedback",
                  value=json.dumps({"id": conversation_id, "score": -1}),
                  label="👎 Not helpful"),
    ]
    await cl.Message(content=answer_data["answer"], actions=actions).send()


@cl.action_callback("feedback")
async def on_feedback(action: cl.Action):
    data = json.loads(action.value)
    db.save_feedback(data["id"], data["score"])
    await cl.Message(content="Feedback recorded — thank you.").send()
