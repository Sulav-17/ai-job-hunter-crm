from __future__ import annotations

import argparse
import json

from backend.database.session import session_scope
from backend.services.demo_seed import seed_demo_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed fictional demo data.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete only demo-marked roots and recreate the deterministic demo dataset.",
    )
    args = parser.parse_args()

    with session_scope() as session:
        report = seed_demo_dataset(session, reset=args.reset)

    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
