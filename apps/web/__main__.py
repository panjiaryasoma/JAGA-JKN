"""Run frontend and API together: uv run --locked python -m apps.web --demo."""

import argparse
import logging
import os
import secrets

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="JAGA-JKN frontend + API lokal")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--demo", action="store_true", help="Buat kunci akses petugas untuk sesi ini"
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.demo:
        print("Kunci akses prototipe lokal; berubah setiap restart --demo.", flush=True)
        for role in ("REVIEWER", "SUPERVISOR"):
            name = f"JAGA_{role}_TOKEN"
            os.environ[name] = secrets.token_urlsafe(32)
            print(f"{role}: {os.environ[name]}", flush=True)
    print(f"Buka http://127.0.0.1:{args.port}/", flush=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uvicorn.run(
        "apps.web.app:app", host="127.0.0.1", port=args.port, access_log=False, log_config=None
    )


if __name__ == "__main__":
    main()
