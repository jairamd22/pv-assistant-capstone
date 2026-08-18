"""CLI for the assistant — runs the agent in-process (no server needed).

Usage:
    python cli.py "Does the gabapentin label cover respiratory depression?"
    python cli.py --no-db "..."   # skip Postgres logging (no DB running)
"""

import argparse
import json
import uuid

from dotenv import load_dotenv
load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="+")
    parser.add_argument("--no-db", action="store_true",
                        help="Don't log to Postgres")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()

    from pv_assistant.agent import MODEL, run_agent

    question = " ".join(args.question)
    result = run_agent(question, model=args.model or MODEL)

    print("\n--- tools used ---")
    for t in result["tool_log"]:
        print(f"  {t['tool']}({t['arguments']})")
    print("\n--- answer ---\n")
    print(result["answer"])
    print(f"\nverdict={result['verdict']} relevance={result['relevance']} "
          f"cost=${result['openai_cost']:.4f} time={result['response_time']:.1f}s")

    if not args.no_db:
        from pv_assistant import db
        db.save_conversation(str(uuid.uuid4()), question, result)
        print("(logged to Postgres)")


if __name__ == "__main__":
    main()
