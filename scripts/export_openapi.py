#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
DEFAULT_OUTPUT = ROOT / "contracts" / "openapi.json"


def render_openapi() -> str:
    os.environ["APP_NAME"] = "Лад API"
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.main import app  # noqa: PLC0415

    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render_openapi()
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            print("OpenAPI snapshot is stale; run make contract-generate.", file=sys.stderr)
            return 1
        print(f"OpenAPI snapshot is current: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"Wrote OpenAPI snapshot: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
