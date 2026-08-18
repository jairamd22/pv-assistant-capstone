"""The agent: an explicit function-calling loop. No framework, on purpose —
owning the orchestration logic directly means every step of tool selection
is explainable and every tool call is logged and inspectable.

Flow: system prompt (with safety framing + verdict format) → LLM decides
which tool(s) to call → tools execute → results appended → repeat until
the LLM answers in text or MAX_ITERS is hit.
"""

import json
import os
import re
from time import time

from openai import OpenAI

from pv_assistant.tools import TOOLS, dispatch

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EVAL_MODEL = os.getenv("EVAL_MODEL", MODEL)
MAX_ITERS = int(os.getenv("AGENT_MAX_ITERS", "6"))

client = OpenAI()

SYSTEM_PROMPT = """
You are a pharmacovigilance intelligence assistant for drug safety
scientists. You have four tools: live adverse-event report lookup
(query_aems), FDA label search (search_labels), regulation search
(search_regulations), and historical safety-labeling-change lookup
(lookup_srlc_history). Call only the tools the question actually needs.

Rules — these are safety-critical:
1. Ground every claim in tool results. Cite the label section name and
   drug (e.g. "Warnings and Precautions, ciprofloxacin") or the regulation
   citation (e.g. "21 CFR 314.80(c)(1)") for every statement of fact.
2. For label-gap questions, end with exactly one verdict line:
   VERDICT: COVERED — the reaction (or a clear synonym) appears in the
     cited label section, OR
   VERDICT: POTENTIAL_GAP — it does not appear in the retrieved sections;
     always say "potential" — absence in retrieval is not proof of
     absence, and terminology mismatch is a known failure mode, OR
   VERDICT: INSUFFICIENT_EVIDENCE — the tools did not return enough to
     decide. Never guess.
3. When you report adverse event counts, always repeat the surveillance
   disclaimer: reports are voluntary passive-surveillance data and do not
   establish causation.
4. You support a human safety reviewer; you do not replace one. Frame gap
   findings as items for human review, not conclusions.
""".strip()


def _extract_verdict(text: str) -> str:
    m = re.search(r"VERDICT:\s*(COVERED|POTENTIAL_GAP|INSUFFICIENT_EVIDENCE)",
                  text or "")
    return m.group(1) if m else "NONE"


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = {  # $ per 1M tokens
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
        "gpt-4.1-mini": (0.40, 1.60),
    }
    inp, out = prices.get(model, (0.0, 0.0))
    return (prompt_tokens * inp + completion_tokens * out) / 1e6


def run_agent(question: str, model: str = MODEL, on_tool=None) -> dict:
    """Run the agent loop. `on_tool(name, args, result)` is an optional
    callback (used by the Chainlit UI to render tool steps live)."""
    t0 = time()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_log = []
    prompt_tokens = completion_tokens = 0

    for _ in range(MAX_ITERS):
        response = client.chat.completions.create(
            model=model, messages=messages, tools=TOOLS,
        )
        prompt_tokens += response.usage.prompt_tokens
        completion_tokens += response.usage.completion_tokens
        msg = response.choices[0].message

        if not msg.tool_calls:
            answer = msg.content or ""
            break

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })
        for tc in msg.tool_calls:
            result = dispatch(tc.function.name, tc.function.arguments)
            tool_log.append({
                "tool": tc.function.name,
                "arguments": tc.function.arguments,
                "result_preview": json.dumps(result, default=str)[:400],
            })
            if on_tool:
                on_tool(tc.function.name, tc.function.arguments, result)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })
    else:
        answer = "I hit my tool-call limit before reaching a grounded answer. VERDICT: INSUFFICIENT_EVIDENCE"

    relevance, explanation, eval_pt, eval_ct = judge(question, answer)
    cost = (calculate_cost(model, prompt_tokens, completion_tokens)
            + calculate_cost(EVAL_MODEL, eval_pt, eval_ct))

    return {
        "answer": answer,
        "verdict": _extract_verdict(answer),
        "tools_used": [t["tool"] for t in tool_log],
        "tool_log": tool_log,
        "model_used": model,
        "response_time": time() - t0,
        "relevance": relevance,
        "relevance_explanation": explanation,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "eval_prompt_tokens": eval_pt,
        "eval_completion_tokens": eval_ct,
        "eval_total_tokens": eval_pt + eval_ct,
        "openai_cost": cost,
    }


JUDGE_PROMPT = """
You are an expert evaluator for an agentic RAG system answering
pharmacovigilance and drug-label questions. Classify the relevance of the
generated answer to the question.

Question: {question}
Generated Answer: {answer}

Provide the output in parsable JSON without using code blocks:

{{"Relevance": "NON_RELEVANT" | "PARTLY_RELEVANT" | "RELEVANT",
  "Explanation": "[brief explanation]"}}
""".strip()


def judge(question: str, answer: str):
    resp = client.chat.completions.create(
        model=EVAL_MODEL,
        messages=[{"role": "user",
                   "content": JUDGE_PROMPT.format(question=question, answer=answer)}],
    )
    pt, ct = resp.usage.prompt_tokens, resp.usage.completion_tokens
    try:
        data = json.loads(resp.choices[0].message.content)
        return data["Relevance"], data["Explanation"], pt, ct
    except (json.JSONDecodeError, KeyError):
        return "UNKNOWN", "Failed to parse evaluation", pt, ct
