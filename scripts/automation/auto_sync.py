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


def analyze_diff(old_sections, new_sections):
    """Analyze changes between two sections.json states."""
    old_keys = set(old_sections.keys())
    new_keys = set(new_sections.keys())
    added_keys = new_keys - old_keys
    
    if not added_keys:
        return []
    
    # Categorize additions
    added_by_family = {}
    for k in added_keys:
        rec = new_sections[k]
        fam = rec.get('family', 'other')
        added_by_family.setdefault(fam, []).append(rec)
    
    bullets = []
    
    # 1. Main story
    if 'main' in added_by_family:
        groups = {r.get('group', {}).get('name') for r in added_by_family['main'] if r.get('group')}
        grp_names = '、'.join(filter(None, groups)) or '全新关卡'
        bullets.append(f"新增主线章节《{grp_names}》（共 {len(added_by_family['main'])} 篇）。")
        
    # 2. Events
    if 'events' in added_by_family:
        groups = {r.get('group', {}).get('name') for r in added_by_family['events'] if r.get('group')}
        grp_names = '、'.join(filter(None, groups)) or '全新限时活动'
        bullets.append(f"新增限时活动《{grp_names}》（共 {len(added_by_family['events'])} 篇关卡剧情）。")
        
    # 3. Characters
    if 'characters' in added_by_family:
        chars = {r.get('group', {}).get('name') for r in added_by_family['characters'] if r.get('group')}
        char_names = '、'.join(filter(None, chars))
        bullets.append(f"新增旅人专属故事：{char_names}（共 {len(added_by_family['characters'])} 篇）。")
        
    # 4. Discs / 秘闻
    if 'discs' in added_by_family:
        bullets.append(f"新增秘闻散文与剧本（共 {len(added_by_family['discs'])} 篇）。")
        
    # 5. Storysets
    if 'storysets' in added_by_family:
        bullets.append(f"新增故事集日常侧写与支线回忆（共 {len(added_by_family['storysets'])} 篇）。")

    # 6. NPC bonds
    if 'npc_bonds' in added_by_family:
        bullets.append(f"新增星塔 NPC 羁绊故事（共 {len(added_by_family['npc_bonds'])} 篇）。")
        
    return bullets


def update_changelog_in_files(today_str, bullets):
    """Write recent update section to site_templates.py and README.md."""
    if not bullets:
        return
    
    # 1. Update site_templates.py
    if os.path.exists(TEMPLATES_PY):
        content = open(TEMPLATES_PY, encoding='utf-8').read()
        # Find update-date-badge and update-list
        date_pattern = r'<span>更新时间：\d{4}-\d{2}-\d{2}</span>'
        new_date = f'<span>更新时间：{today_str}</span>'
        content = re.sub(date_pattern, new_date, content)
        
        # Pill date in hero
        pill_pattern = r'<span class="pill-date">\d{4}-\d{2}-\d{2}</span>'
        new_pill = f'<span class="pill-date">{today_str}</span>'
        content = re.sub(pill_pattern, new_pill, content)
        
        # Generate new update list items
        list_html = '\n'.join(f'      <li>{b}</li>' for b in bullets)
        list_pattern = r'(<ul class="update-list">\s*)(.*?)(\s*</ul>)'
        content = re.sub(list_pattern, r'\1' + list_html + r'\3', content, flags=re.S)
        
        with open(TEMPLATES_PY, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[Changelog] Updated {TEMPLATES_PY} with {len(bullets)} items.")

    # 2. Update README.md
    if os.path.exists(README_MD):
        readme = open(README_MD, encoding='utf-8').read()
        readme_bullets = '\n'.join(f'- {b}' for b in bullets)
        new_entry = f"### 📅 {today_str}\n{readme_bullets}\n"
        
        # Insert after ## 🔄 最近更新记录
        marker = '## 🔄 最近更新记录\n\n'
        if marker in readme:
            parts = readme.split(marker, 1)
            readme = parts[0] + marker + new_entry + '\n' + parts[1]
            with open(README_MD, 'w', encoding='utf-8') as f:
                f.write(readme)
            print(f"[Changelog] Updated {README_MD} with new entry.")


def main():
    parser = argparse.ArgumentParser(description="StellaSora Automated Sync Pipeline")
    parser.add_argument('--check-only', action='store_true', help='Only check if both upstreams updated')
    parser.add_argument('--force', action='store_true', help='Force full sync and rebuild')
    parser.add_argument('--allow-single-upstream', action='store_true', help='Proceed even if only one upstream updated')
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

    # Diff analysis
    bullets = analyze_diff(old_sections, new_sections)
    tz = timezone(timedelta(hours=8))
    today_str = datetime.now(tz).strftime('%Y-%m-%d')

    if bullets:
        print(f"[Diff] Detected {len(bullets)} new additions:")
        for b in bullets:
            print(f"  • {b}")
        update_changelog_in_files(today_str, bullets)
    else:
        print("[Diff] No new chapters/events added (may be table typo fixes or metadata adjustments).")

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
            summary_msg = f"自动同步上游剧情 ({today_str}): " + ('; '.join(bullets) if bullets else "同步微调与修复")
            f.write(f"commit_msg={summary_msg}\n")
    print("[Success] All sync, extraction, build, and validation steps completed successfully!")


if __name__ == '__main__':
    main()
