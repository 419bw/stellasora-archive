# -*- coding: utf-8 -*-
"""Automated sync and changelog generation for StellaSora story knowledge base.

Checks upstream repositories (StellaSoraData & ss-lua) for new commits, pulls
latest assets when both have updated, regenerates story docs, writes human-readable
changelogs, rebuilds the static site, and verifies with test suite.
"""

import sys
import os
import re
import json
import argparse
import subprocess
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE_FILE = os.path.join(ROOT, '.upstream_sync_state.json')

UPSTREAM_DATA_REPO = 'https://github.com/AutumnVN/StellaSoraData.git'
UPSTREAM_LUA_REPO = 'https://github.com/MakoStar/ss-lua.git'

DATA_DIR = os.path.join(ROOT, 'data', 'StellaSoraData')
LUA_DIR = os.path.join(ROOT, 'data', 'ss_lua')
SECTIONS_JSON = os.path.join(ROOT, 'story_docs', '_data', 'sections.json')
TEMPLATES_PY = os.path.join(ROOT, 'scripts', 'site', 'site_templates.py')
README_MD = os.path.join(ROOT, 'README.md')


def get_remote_head(url):
    """Retrieve the HEAD commit hash using git ls-remote (no API rate limit)."""
    try:
        res = subprocess.run(
            ['git', 'ls-remote', url, 'HEAD'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30
        )
        if res.returncode == 0 and res.stdout:
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == 'HEAD':
                    return parts[0]
        return None
    except Exception as e:
        print(f"[Error] Failed to query {url}: {e}", file=sys.stderr)
        return None


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE, encoding='utf-8'))
        except Exception:
            pass
    return {
        'last_synced_at': None,
        'stella_sora_data_commit': None,
        'ss_lua_commit': None
    }


def save_state(data_commit, lua_commit):
    tz = timezone(timedelta(hours=8))
    now_str = datetime.now(tz).strftime('%Y-%m-%dT%H:%M:%S+08:00')
    state = {
        'last_synced_at': now_str,
        'stella_sora_data_commit': data_commit,
        'ss_lua_commit': lua_commit
    }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f"[Sync] Saved state to {STATE_FILE}")


def sync_repo(url, target_dir):
    """Clone or pull latest upstream repo with shallow clone."""
    os.makedirs(os.path.dirname(target_dir), exist_ok=True)
    if os.path.exists(os.path.join(target_dir, '.git')):
        print(f"[Sync] Fetching {url} in {target_dir}...")
        subprocess.run(['git', '-C', target_dir, 'fetch', '--depth', '1', 'origin'], check=True)
        subprocess.run(['git', '-C', target_dir, 'reset', '--hard', 'origin/HEAD'], check=True)
    else:
        print(f"[Sync] Shallow cloning {url} into {target_dir}...")
        if os.path.exists(target_dir):
            import shutil
            shutil.rmtree(target_dir)
        subprocess.run(['git', 'clone', '--depth', '1', url, target_dir], check=True)


# ---------------------------------------------------------------------------
# Changelog: collapse sections.json diffs into a single one-line reason.
# ---------------------------------------------------------------------------

# family -> human label; order here == display order in the reason string.
_FAMILY_LABEL = [
    ('main', '主线剧情'),
    ('events', '限时活动'),
    ('characters', '旅人专属故事'),
    ('discs', '秘闻'),
    ('storysets', '故事集支线'),
    ('npc_bonds', '星塔 NPC 羁绊'),
]
_FAMILY_KNOWN = {fam for fam, _ in _FAMILY_LABEL}
_OTHER_LABEL = '其他剧情'
# Used when upstream changed but no new pages were added (pure fixes / re-extract).
_GENERIC_REASON = '上游数据与剧本文案修正'


def _pages_map(sections):
    """sections.json payload -> {(family, id): record}. Tolerant of empty/legacy input."""
    if not isinstance(sections, dict):
        return {}
    out = {}
    for p in (sections.get('pages') or []):
        if isinstance(p, dict):
            out[(p.get('family'), p.get('id'))] = p
    return out


def _reason_line(added_by_family):
    """Collapse per-family additions into a single human-readable reason sentence."""
    total = sum(len(v) for v in added_by_family.values())
    if total == 0:
        return _GENERIC_REASON
    labels = [label for fam, label in _FAMILY_LABEL if fam in added_by_family]
    if any(fam not in _FAMILY_KNOWN for fam in added_by_family):   # e.g. battles_unmounted / prologue
        labels.append(_OTHER_LABEL)
    return "更新" + "、".join(labels) + f"，新增 {total} 篇内容"


def analyze_diff(old_sections, new_sections):
    """Analyze additions between two sections.json states.

    Returns a one-line changelog reason string, or None when there is no usable
    baseline (fresh init / empty state). The caller treats None as "skip writing
    a changelog" rather than reporting the entire library as newly added.
    """
    old_map = _pages_map(old_sections)
    new_map = _pages_map(new_sections)
    if not old_map:
        return None
    added = [new_map[k] for k in (set(new_map) - set(old_map))]
    added_by_family = {}
    for rec in added:
        added_by_family.setdefault(rec.get('family', 'other'), []).append(rec)
    return _reason_line(added_by_family)


def _esc_html(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _resolve_reason(auto_reason, note_arg):
    """D2: an explicit note (CLI --note / STELLA_SYNC_NOTE env) overrides the auto reason."""
    return (note_arg or '').strip() or auto_reason


def _today_str():
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime('%Y-%m-%d')


def _write_homepage_markers(today_str, reason):
    """Rewrite the homepage date badge / hero pill / pill-text / update-summary."""
    if not os.path.exists(TEMPLATES_PY):
        return
    r_home = _esc_html(reason)
    content = open(TEMPLATES_PY, encoding='utf-8').read()
    content = re.sub(r'<span>更新时间：\d{4}-\d{2}-\d{2}</span>',
                     lambda m: f'<span>更新时间：{today_str}</span>', content)
    content = re.sub(r'<span class="pill-date">\d{4}-\d{2}-\d{2}</span>',
                     lambda m: f'<span class="pill-date">{today_str}</span>', content)
    content = re.sub(r'<span class="pill-text">[^<]*</span>',
                     lambda m: f'<span class="pill-text">上次更新：{r_home}</span>', content)
    content = re.sub(r'<div class="update-summary">[^<]*</div>',
                     lambda m: f'<div class="update-summary">{r_home}</div>', content)
    with open(TEMPLATES_PY, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[Changelog] Updated {TEMPLATES_PY}: {reason}")


def _readme_write_latest(today_str, lines):
    """Keep ONLY the newest entry under "## 最近更新记录"; drop every older one.

    The section body is replaced wholesale on each write, so the README never
    grows across runs (old entries are intentionally discarded, not archived).
    The trailing "---" separator and any following section are preserved so the
    document structure stays intact.
    """
    if not os.path.exists(README_MD) or not lines:
        return
    readme = open(README_MD, encoding='utf-8').read()
    marker = '## 最近更新记录\n\n'
    if marker not in readme:
        return
    head, _, tail = readme.partition(marker)
    # Everything from the first section separator (or the next heading) onwards
    # belongs to the rest of the document and must survive untouched.
    m = re.search(r'\n---\n|\n## ', tail)
    rest = tail[m.start():] if m else ''
    body = ''.join(f'- {ln}\n' for ln in lines)
    with open(README_MD, 'w', encoding='utf-8') as f:
        f.write(f"{head}{marker}### {today_str}\n{body}{rest}")
    print(f"[Changelog] Updated {README_MD}: {today_str}")


def update_changelog_in_files(today_str, reason):
    """Write the recent-update date + one-line reason into site_templates.py and README.md."""
    reason = ' '.join((reason or '').split()).strip()
    if not reason:
        return
    _write_homepage_markers(today_str, reason)
    _readme_write_latest(today_str, [reason])


# ---------------------------------------------------------------------------
# Commit-driven changelog (push events)
# ---------------------------------------------------------------------------

# Conventional-commit prefixes that carry no user-facing information.
_NOISE_PREFIXES = ('chore:', 'ci:', 'style:')
# Safety cap: a squash / force-push can otherwise dump a huge list into the README.
_MAX_COMMIT_ENTRIES = 10
# Unit separator, so a commit subject containing the delimiter cannot break parsing.
_US = '\x1f'


def collect_commits(rev_range=None, limit=200):
    """Return [(sha, author_name, author_email, subject)], newest first.

    `rev_range` is a revision expression such as 'A..B'; when omitted the most
    recent `limit` commits of HEAD are used. Any git failure yields [] so the
    caller can degrade gracefully instead of breaking the pipeline.
    """
    rev = rev_range.split() if rev_range else []
    fmt = f'%H{_US}%an{_US}%ae{_US}%s'
    cmd = ['git', 'log', '--no-merges', '--max-count', str(limit), f'--format={fmt}'] + rev
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
    except Exception as e:
        print(f"[Changelog] git log failed: {e}", file=sys.stderr)
        return []
    if res.returncode != 0:
        print(f"[Changelog] git log error: {res.stderr.strip()}", file=sys.stderr)
        return []
    commits = []
    for line in res.stdout.splitlines():
        parts = line.split(_US)
        if len(parts) == 4:
            commits.append((parts[0], parts[1], parts[2], parts[3].strip()))
    return commits


def filter_human_commits(commits):
    """Keep only user-facing commits: drop bots, merges and chore/ci/style housekeeping."""
    kept = []
    for sha, name, email, subject in commits:
        if 'github-actions' in (email or '').lower() or '[bot]' in (name or '').lower():
            continue
        s = (subject or '').strip()
        if not s or s.lower().startswith('merge '):
            continue
        if s.lower().startswith(_NOISE_PREFIXES):
            continue
        kept.append((sha, name, email, s))
    return kept


def update_changelog_from_commits(today_str, commits):
    """Homepage gets a one-line summary; README keeps the full commit list.

    Returns True when something was written, so the caller can decide to commit.
    """
    recorded = list(commits)[:_MAX_COMMIT_ENTRIES]
    if not recorded:
        print("[Changelog] No user-facing commits to record.")
        return False
    subjects = [c[3] for c in recorded]
    summary = f"同步 {len(subjects)} 项代码更新"
    _write_homepage_markers(today_str, summary)
    _readme_write_latest(today_str, subjects)
    return True


def main():
    parser = argparse.ArgumentParser(description="StellaSora Automated Sync Pipeline")
    parser.add_argument('--check-only', action='store_true', help='Only check if both upstreams updated')
    parser.add_argument('--force', action='store_true', help='Force full sync and rebuild')
    parser.add_argument('--allow-single-upstream', action='store_true', help='Proceed even if only one upstream updated')
    parser.add_argument('--note', default=None,
                        help='Manually override the changelog reason for this sync (defaults to auto-derived).')
    args = parser.parse_args()

    state = load_state()
    cur_data_commit = state.get('stella_sora_data_commit')
    cur_lua_commit = state.get('ss_lua_commit')

    print("[Sync] Checking upstream commit SHAs...")
    latest_data_head = get_remote_head(UPSTREAM_DATA_REPO)
    latest_lua_head = get_remote_head(UPSTREAM_LUA_REPO)

    if not latest_data_head or not latest_lua_head:
        print("[Error] Failed to fetch remote commit SHAs for one or both upstreams.", file=sys.stderr)
        sys.exit(1)

    print(f"[Sync] StellaSoraData HEAD: {latest_data_head[:10]} (current: {str(cur_data_commit)[:10]})")
    print(f"[Sync] ss-lua          HEAD: {latest_lua_head[:10]} (current: {str(cur_lua_commit)[:10]})")

    data_updated = (latest_data_head != cur_data_commit)
    lua_updated = (latest_lua_head != cur_lua_commit)

    if args.allow_single_upstream:
        should_sync = (data_updated or lua_updated)
    else:
        # Default: both upstreams must be updated, or force
        should_sync = (data_updated and lua_updated)

    if args.force:
        should_sync = True

    if args.check_only:
        print(f"data_updated={data_updated}")
        print(f"lua_updated={lua_updated}")
        print(f"should_sync={should_sync}")
        sys.exit(0)

    if not should_sync:
        if data_updated and not lua_updated:
            print("[Info] StellaSoraData has new commit, but ss-lua is not updated yet. Waiting for both.")
        elif lua_updated and not data_updated:
            print("[Info] ss-lua has new commit, but StellaSoraData is not updated yet. Waiting for both.")
        else:
            print("[Info] Both upstreams are up to date. Nothing to do.")

        # Write to GITHUB_OUTPUT if running in GitHub Actions
        gh_out = os.environ.get('GITHUB_OUTPUT')
        if gh_out:
            with open(gh_out, 'a', encoding='utf-8') as f:
                f.write("has_updates=false\n")
        return

    print("[Sync] Sync condition met. Pulling upstream repositories...")
    sync_repo(UPSTREAM_DATA_REPO, DATA_DIR)
    sync_repo(UPSTREAM_LUA_REPO, LUA_DIR)

    # Load pre-build sections state
    old_sections = {}
    if os.path.exists(SECTIONS_JSON):
        try:
            old_sections = json.load(open(SECTIONS_JSON, encoding='utf-8'))
        except Exception:
            pass

    print("[Build] Running scripts/story/build_story.py...")
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'story', 'build_story.py')], check=True)

    # Load post-build sections state
    new_sections = {}
    if os.path.exists(SECTIONS_JSON):
        new_sections = json.load(open(SECTIONS_JSON, encoding='utf-8'))

    # Diff analysis -> single one-line reason (None => no baseline / fresh init)
    reason = analyze_diff(old_sections, new_sections)
    today_str = _today_str()
    display_reason = _resolve_reason(reason, args.note or os.environ.get('STELLA_SYNC_NOTE'))

    if display_reason:
        # D3: every successful sync refreshes date + reason; note (D2) overrides auto reason.
        print(f"[Diff] Recent update: {display_reason}")
        update_changelog_in_files(today_str, display_reason)   # MUST precede build_site.py
    else:
        print("[Diff] No baseline sections.json; skipping changelog (initial baseline).")
    commit_reason = display_reason or _GENERIC_REASON

    print("[Build] Running scripts/site/build_site.py...")
    subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'site', 'build_site.py')], check=True)

    print("[Test] Running tests/story/validate_site.py...")
    subprocess.run([sys.executable, os.path.join(ROOT, 'tests', 'story', 'validate_site.py')], check=True)

    # Save state
    save_state(latest_data_head, latest_lua_head)

    # Output to GitHub Actions
    gh_out = os.environ.get('GITHUB_OUTPUT')
    if gh_out:
        with open(gh_out, 'a', encoding='utf-8') as f:
            f.write("has_updates=true\n")
            summary_msg = f"自动同步上游剧情 ({today_str}): {commit_reason}"
            f.write(f"commit_msg={summary_msg}\n")
    print("[Success] All sync, extraction, build, and validation steps completed successfully!")


if __name__ == '__main__':
    main()
