"""Inspect or synchronize the Aura graph without starting the API server."""

import argparse
import json

from backend.app.services.movement_network import configured, projection_status, sync_projection


def main() -> None:
    parser = argparse.ArgumentParser(description="WildTrack Neo4j Aura movement projection")
    parser.add_argument("action", choices=("status", "sync"))
    parser.add_argument("--force", action="store_true", help="Rebuild even when source records are unchanged")
    args = parser.parse_args()
    if args.action == "sync" and not configured():
        parser.error("Add NEO4J_URI, NEO4J_USERNAME and NEO4J_PASSWORD to the backend .env file first")
    result = projection_status() if args.action == "status" else sync_projection(force=args.force)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
