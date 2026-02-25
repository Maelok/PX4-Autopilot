#!/usr/bin/env python3
"""Validate that a PR title follows PX4's 'subsystem: description' convention."""

import re
import sys

# subsystem prefix, colon, space, then at least 5 chars of description
TITLE_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_/\-\. ]*: .{5,}')

# Titles that are exempt from the subsystem pattern
EXEMPT_PREFIXES = ('Revert "', 'Merge ')


def check_title(title: str) -> bool:
    title = title.strip()

    if not title:
        print("PR title is empty.", file=sys.stderr)
        return False

    for prefix in EXEMPT_PREFIXES:
        if title.startswith(prefix):
            return True

    if TITLE_PATTERN.match(title):
        return True

    print(
        f"PR title does not match the expected format.\n"
        f"\n"
        f"  Title: {title}\n"
        f"\n"
        f"Expected pattern:  subsystem: short description (5+ chars)\n"
        f"\n"
        f"Good examples:\n"
        f'  ekf2: fix height fusion timeout\n'
        f'  mavlink: add BATTERY_STATUS_V2 support\n'
        f'  boards/px4_fmu-v6x: enable UAVCAN\n'
        f'  CI: migrate to reusable workflows\n'
        f"\n"
        f"Bad examples:\n"
        f'  fix stuff\n'
        f'  Update file\n'
        f'  changes\n',
        file=sys.stderr,
    )
    return False


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <pr-title>", file=sys.stderr)
        sys.exit(2)

    if check_title(sys.argv[1]):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
