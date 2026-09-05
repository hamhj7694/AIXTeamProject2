"""Service entrypoint; environment files are injected by systemd, never searched."""
import argparse
import os

import uvicorn

from backend.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("service", choices=["general", "ai"])
    args = parser.parse_args()
    settings = Settings.from_environment()
    if args.service == "general":
        host = os.getenv("GENERAL_API_HOST", "127.0.0.1")
        port = int(os.getenv("GENERAL_API_PORT", "8100"))
        default_port = 8100
    else:
        host = os.getenv("AI_API_HOST", "127.0.0.1")
        port = int(os.getenv("AI_API_PORT", "8101"))
        default_port = 8101
    if host != "127.0.0.1" or not 1 <= port <= 65535:
        raise SystemExit("APIs must bind to a valid loopback port")
    if settings.app_env == "production" and port != default_port:
        raise SystemExit("Production ports must be General 8100 and AI 8101")
    uvicorn.run(f"backend.{args.service}_api.app.main:app", host=host, port=port, access_log=False)


if __name__ == "__main__":
    main()
