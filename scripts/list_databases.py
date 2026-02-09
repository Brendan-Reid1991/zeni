#!/usr/bin/env python3
"""Script to list all SQLAlchemy databases saved in the zeni folder."""

import argparse
from pathlib import Path

from zeni.database.utils import DEFAULT_PATHWAY, list_databases


def main():
    parser = argparse.ArgumentParser(
        description="List all saved SQLAlchemy databases in the zeni folder"
    )
    parser.add_argument(
        "--path",
        "-p",
        default=DEFAULT_PATHWAY,
        help=f"Path to database folder (default: {DEFAULT_PATHWAY})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show full paths instead of just database names",
    )

    args = parser.parse_args()

    databases = list_databases(args.path)

    if not databases:
        print(f"No databases found in '{args.path}'")
        return

    print(f"Found {len(databases)} database(s) in '{args.path}':")

    for db in databases:
        if args.verbose:
            full_path = Path(args.path) / f"{db}.db"
            print(f"  - {db} ({full_path.resolve()})")
        else:
            print(f"  - {db}")


if __name__ == "__main__":
    main()
