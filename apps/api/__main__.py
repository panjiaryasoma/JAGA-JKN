"""Local prototype launcher: uv run --locked python -m apps.api."""

import argparse
import logging
import os
import secrets

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="JAGA-JKN local synthetic backend")
    parser.add_argument("--port", type=int, default=8000, help="Loopback port (default: 8000)")
    parser.add_argument(
        "--demo", action="store_true", help="Generate and print process-only demo credentials"
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.demo:
        print("Local synthetic demo. Credentials rotate when --demo is restarted.", flush=True)
        for role in ("REVIEWER", "SUPERVISOR"):
            name = f"JAGA_{role}_TOKEN"
            os.environ[name] = secrets.token_urlsafe(32)
            print(f"{name}={os.environ[name]}", flush=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(
        "apps.api.main:app", host="127.0.0.1", port=args.port, access_log=False, log_config=None
    )


if __name__ == "__main__":
    main()
