"""Run and retain the bridge/port foundation vertical."""

from __future__ import annotations

import argparse
from pathlib import Path

from .concordia_runtime import run_bridge_port_vertical


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = run_bridge_port_vertical()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.force:
        raise FileExistsError(f"refusing to overwrite retained artifact: {args.output}")
    args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
