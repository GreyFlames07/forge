from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python apps/cli/src/main.py [health|status|report]")
        return 1
    if argv[0] == "health":
        print("ok")
        return 0
    if argv[0] == "status":
        print(json.dumps({"status": "ok", "source": "minimal-cli"}))
        return 0
    if argv[0] == "report":
        print(json.dumps({"report": "daily-summary", "status": "generated"}))
        return 0
    print(f"unknown command: {argv[0]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
