#!/usr/bin/env python3
"""Verify PR commits' author-matching DCO trailers. A CI check is not independent approval."""
import re
import subprocess
import sys

TRAILER = re.compile(r"^Signed-off-by: ([^<>\\n]+) <([^<>\\n]+)>$", re.IGNORECASE)


def signoff_matches(author_name, author_email, message):
    # Only accept an exact footer at the end of the message, not text embedded in prose.
    lines = message.rstrip().splitlines()
    footer = []
    for line in reversed(lines):
        if not line.strip():
            break
        footer.append(line.strip())
    trailers = [TRAILER.fullmatch(line) for line in footer]
    return any(m and m.group(1) == author_name and m.group(2) == author_email for m in trailers)


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def check_range(base, head):
    if not all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in (base, head)):
        raise ValueError("base and head must be 40-character lowercase Git object IDs")
    commits = git("rev-list", "--reverse", f"{base}..{head}").splitlines()
    if not commits:
        raise ValueError("no PR commits to validate")
    errors = []
    for commit in commits:
        details = git("show", "-s", "--format=%an%x00%ae%x00%B", commit)
        parts = details.split("\x00", 2)
        if len(parts) != 3 or not signoff_matches(*parts):
            errors.append(f"missing author-matching footer on commit {commit}")
    return errors


def main(argv):
    if len(argv) != 3:
        raise ValueError("usage: check_dco.py BASE_SHA HEAD_SHA")
    failures = check_range(argv[1], argv[2])
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        return 1
    print("DCO: all PR commits have an author-matching Signed-off-by trailer")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"DCO verification could not complete: {exc}", file=sys.stderr)
        raise SystemExit(1)
