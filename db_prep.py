"""Initialize the Postgres schema. Run once after `docker-compose up postgres`."""

import os

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("POSTGRES_HOST", "localhost")

from pv_assistant import db  # noqa: E402

if __name__ == "__main__":
    print("Initializing database...")
    db.init_db()
    print("Done.")
