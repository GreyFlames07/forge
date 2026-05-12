from __future__ import annotations

import json
import sys


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if "--healthcheck" in argv:
        print("worker-ok")
        return 0
    if "--run-once" in argv:
        print(json.dumps({"job": "demo", "result": "processed"}))
        return 0
    print("usage: python apps/worker/src/main.py [--healthcheck|--run-once]")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
