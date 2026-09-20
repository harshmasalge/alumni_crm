#!/usr/bin/env python
"""
Local entry point for the fictional demo bootstrap.

Runs the same code the API lifespan runs on staging/demo hosts, against
your local database after migrations:

    DEMO_SEED=true DEMO_PASSWORD=demo1234 python scripts/seed_demo.py

Fictional data only. Refuses to run when ENVIRONMENT=production.
See app.db.demo_bootstrap for the full contract.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app.db.demo_bootstrap import run_demo_bootstrap


async def main() -> None:
    await run_demo_bootstrap()
    print("Demo bootstrap finished (see log line above for counts).")


if __name__ == "__main__":
    asyncio.run(main())
