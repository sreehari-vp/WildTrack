"""Run with: python -m backend.app.export_history export|status|verify."""

import argparse
import json
from pathlib import Path

from backend.app.core.config import ROOT_DIR
from backend.app.services.historical_export import (
    export_incremental, export_status, verify_export_files,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="WildTrack incremental historical export")
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="Write new PostgreSQL records as local Parquet")
    export.add_argument("--output-dir", type=Path, default=ROOT_DIR / "historical_exports")
    export.add_argument("--batch-size", type=int, default=1000)
    export.add_argument("--max-batches", type=int, default=100)
    sub.add_parser("status", help="Show export ledger counts")
    sub.add_parser("verify", help="Check saved Parquet files, hashes and row counts")
    args = parser.parse_args()

    if args.command == "export":
        result = export_incremental(args.output_dir, batch_size=args.batch_size, max_batches=args.max_batches)
    elif args.command == "status":
        result = export_status()
    elif args.command == "verify":
        errors = verify_export_files()
        result = {"ok": not errors, "errors": errors}
        print(json.dumps(result, indent=2, default=str))
        if errors:
            raise SystemExit(1)
        return
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
