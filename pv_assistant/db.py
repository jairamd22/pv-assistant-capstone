"""Postgres logging: conversations, feedback, per-call tool log, and SrLC
validation results (feeds the two new Grafana panels)."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import DictCursor

TZ_INFO = os.getenv("TZ", "America/Los_Angeles")
tz = ZoneInfo(TZ_INFO)


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "pv_assistant"),
        user=os.getenv("POSTGRES_USER", "user"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )


def init_db():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS tool_calls")
            cur.execute("DROP TABLE IF EXISTS feedback")
            cur.execute("DROP TABLE IF EXISTS srlc_validation")
            cur.execute("DROP TABLE IF EXISTS conversations")

            cur.execute("""
                CREATE TABLE conversations (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    tools_used TEXT NOT NULL,
                    model_used TEXT NOT NULL,
                    response_time FLOAT NOT NULL,
                    relevance TEXT NOT NULL,
                    relevance_explanation TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    eval_prompt_tokens INTEGER NOT NULL,
                    eval_completion_tokens INTEGER NOT NULL,
                    eval_total_tokens INTEGER NOT NULL,
                    openai_cost FLOAT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE feedback (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT REFERENCES conversations(id),
                    feedback INTEGER NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE tool_calls (
                    id SERIAL PRIMARY KEY,
                    conversation_id TEXT REFERENCES conversations(id),
                    tool_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE srlc_validation (
                    id SERIAL PRIMARY KEY,
                    drug TEXT NOT NULL,
                    reaction TEXT NOT NULL,
                    change_date DATE NOT NULL,
                    flagged BOOLEAN NOT NULL,
                    verdict TEXT NOT NULL,
                    run_at TIMESTAMP WITH TIME ZONE NOT NULL
                )
            """)
        conn.commit()
    finally:
        conn.close()


def save_conversation(conversation_id, question, answer_data, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations
                (id, question, answer, verdict, tools_used, model_used,
                 response_time, relevance, relevance_explanation,
                 prompt_tokens, completion_tokens, total_tokens,
                 eval_prompt_tokens, eval_completion_tokens, eval_total_tokens,
                 openai_cost, timestamp)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    conversation_id, question, answer_data["answer"],
                    answer_data["verdict"], ",".join(answer_data["tools_used"]),
                    answer_data["model_used"], answer_data["response_time"],
                    answer_data["relevance"], answer_data["relevance_explanation"],
                    answer_data["prompt_tokens"], answer_data["completion_tokens"],
                    answer_data["total_tokens"], answer_data["eval_prompt_tokens"],
                    answer_data["eval_completion_tokens"], answer_data["eval_total_tokens"],
                    answer_data["openai_cost"], timestamp,
                ),
            )
            for t in answer_data.get("tool_log", []):
                cur.execute(
                    "INSERT INTO tool_calls (conversation_id, tool_name, arguments, timestamp) "
                    "VALUES (%s, %s, %s, %s)",
                    (conversation_id, t["tool"], t["arguments"], timestamp),
                )
        conn.commit()
    finally:
        conn.close()


def save_feedback(conversation_id, feedback, timestamp=None):
    if timestamp is None:
        timestamp = datetime.now(tz)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO feedback (conversation_id, feedback, timestamp) VALUES (%s,%s,%s)",
                (conversation_id, feedback, timestamp),
            )
        conn.commit()
    finally:
        conn.close()


def save_srlc_result(drug, reaction, change_date, flagged, verdict, run_at=None):
    if run_at is None:
        run_at = datetime.now(tz)
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO srlc_validation (drug, reaction, change_date, flagged, verdict, run_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (drug, reaction, change_date, flagged, verdict, run_at),
            )
        conn.commit()
    finally:
        conn.close()
