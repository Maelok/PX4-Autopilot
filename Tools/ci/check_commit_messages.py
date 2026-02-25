#!/usr/bin/env python3
"""Validate commit messages in a PR against PX4 conventions.

Reads a JSON array of GitHub commit objects from stdin (as returned by the
GitHub API's /pulls/{n}/commits endpoint) and checks each message for
blocking errors and advisory warnings.
"""

import json
import re
import sys

# Blocking: prefixes that indicate unsquashed fixup commits
FIXUP_PREFIXES = ('fixup!', 'squash!', 'amend!')

# Blocking: single-word throwaway messages (case-insensitive exact match)
THROWAWAY_WORDS = frozenset({
    'fix', 'fixed', 'fixes',
    'update', 'updated', 'updates',
    'test', 'tests', 'testing',
    'tmp', 'temp',
    'oops', 'wip',
    'debug', 'cleanup',
})

# Blocking: debug session leftovers
DEBUG_KEYWORDS = ('tmate',)

# Warning: review-response messages (case-insensitive substring match)
REVIEW_RESPONSE_PATTERNS = (
    'address review',
    'apply suggestions from code review',
    'code review',
)

# Warning: formatter-only commits
FORMATTER_PATTERNS = (
    'do make format',
    'make format',
    'run formatter',
    'apply format',
)

# Advisory: subsystem prefix pattern
SUBSYSTEM_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_/\-\. ]*: ')

MIN_MESSAGE_LENGTH = 5


def check_commit(message: str) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for a single commit message."""
    errors: list[str] = []
    warnings: list[str] = []

    first_line = message.split('\n', 1)[0].strip()
    lower = first_line.lower()

    # --- Blocking checks ---

    for prefix in FIXUP_PREFIXES:
        if lower.startswith(prefix):
            errors.append(f'Unsquashed commit: starts with "{prefix}"')

    if lower == 'wip' or lower.startswith('wip ') or lower.startswith('wip:'):
        errors.append('WIP commit should not be merged')

    if len(first_line) < MIN_MESSAGE_LENGTH:
        errors.append(f'Message too short ({len(first_line)} chars, minimum {MIN_MESSAGE_LENGTH})')

    if first_line.strip() and first_line.strip().lower() in THROWAWAY_WORDS:
        errors.append(f'Single-word throwaway message: "{first_line.strip()}"')

    for kw in DEBUG_KEYWORDS:
        if kw in lower:
            errors.append(f'Debug session leftover: contains "{kw}"')

    # --- Warning checks ---

    for pattern in REVIEW_RESPONSE_PATTERNS:
        if pattern in lower:
            warnings.append(f'Review-response commit: consider squashing before merge')
            break

    for pattern in FORMATTER_PATTERNS:
        if pattern in lower:
            warnings.append('Formatter-only commit: consider squashing into parent commit')
            break

    if not SUBSYSTEM_PATTERN.match(first_line):
        # Exempt merge and revert commits
        if not first_line.startswith('Revert "') and not first_line.startswith('Merge '):
            warnings.append('Missing subsystem prefix (e.g. "ekf2: fix something")')

    return errors, warnings


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Failed to parse JSON input: {exc}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(data, list):
        print("Expected a JSON array of commit objects.", file=sys.stderr)
        sys.exit(2)

    has_blocking = False
    has_warnings = False

    for commit in data:
        sha = commit.get('sha', '?')[:10]
        message = commit.get('commit', {}).get('message', '')
        first_line = message.split('\n', 1)[0].strip()

        errors, warnings = check_commit(message)

        if errors or warnings:
            print(f"\n  {sha}  {first_line}")

        for err in errors:
            print(f"    ERROR: {err}")
            has_blocking = True

        for warn in warnings:
            print(f"    WARNING: {warn}")
            has_warnings = True

    if has_blocking:
        print(
            "\n"
            "Commit message errors must be fixed before merging.\n"
            "\n"
            "To clean up commits:\n"
            "  git rebase -i HEAD~N        # mark fixup/bad commits for squash\n"
            "  git commit --fixup=<sha>     # create a fixup commit, then\n"
            "  git rebase -i --autosquash   # auto-reorder and squash\n"
            "  git push --force-with-lease  # update the PR branch\n",
            file=sys.stderr,
        )
        sys.exit(1)

    if has_warnings:
        print(
            "\nWarnings above are advisory. Consider cleaning up before merge.",
            file=sys.stderr,
        )

    sys.exit(0)


if __name__ == '__main__':
    main()
