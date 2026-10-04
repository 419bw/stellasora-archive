#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Record a push's own commits into the site changelog (homepage pill + README).

Runs from .github/workflows/deploy.yml on `push` events, BEFORE the site is
rebuilt, so the freshly written markers are baked into the deployed pages.

Behaviour (see the design that shipped with the changelog fix):
  * only user-facing commits are kept -- bots, merge commits and chore/ci/style
    housekeeping are dropped;
  * the commit list is capped so a squash / force-push cannot flood the README;
  * the homepage keeps a one-line summary, README keeps the full list;
  * writing is idempotent for the same day, so repeat runs never duplicate an
    entry.

Exit code is always 0 unless something unexpected breaks: the caller relies on
the `updated` GitHub output to decide whether a commit is needed, and a broken
changelog must never fail the deploy.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import auto_sync  # noqa: E402  (sibling module: owns paths + changelog writers)


def main():
    parser = argparse.ArgumentParser(description="Write push commits into the docs changelog")
    parser.add_argument('--range', dest='rev_range', default=None,
                        help="Git revision expression such as 'A..B'. "
                             "Defaults to the COMMIT_RANGE env var, else recent HEAD.")
    parser.add_argument('--note', default=None,
                        help="Ignored here; kept for CLI compatibility with auto_sync.py.")
    args = parser.parse_args()

    rev_range = args.rev_range or os.environ.get('COMMIT_RANGE') or None
    commits = auto_sync.collect_commits(rev_range)
    if not commits and rev_range:
        # `github.event.before` is all-zero / not an ancestor (new branch, force-push).
        print("[Changelog] Range yielded nothing; falling back to recent HEAD.")
        commits = auto_sync.collect_commits(None)

    kept = auto_sync.filter_human_commits(commits)
    print(f"[Changelog] {len(commits)} commit(s) scanned, {len(kept)} kept after filtering.")

    today = auto_sync._today_str()
    changed = auto_sync.update_changelog_from_commits(today, kept)

    gh_out = os.environ.get('GITHUB_OUTPUT')
    if gh_out:
        with open(gh_out, 'a', encoding='utf-8') as f:
            f.write(f"updated={'true' if changed else 'false'}\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
