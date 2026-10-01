# -*- coding: utf-8 -*-
"""
run_benchmark.py
Offline evaluation benchmark for the Stella Sora Wiki knowledge base.
Simulates multi-turn tool-calling retrieval:
1. Alias Table / Inverted Index lookup
2. Progressive disclosure document viewing
3. Fact verification against official datamine standards
"""

import os
import sys
import json
import re

sys.stdout.reconfigure(encoding='utf-8')

KB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
ALIAS_INDEX = os.path.join(KB_DIR, 'alias_index.json')

def load_alias_index():
    with open(ALIAS_INDEX, 'r', encoding='utf-8') as f:
        return json.load(f)

def retrieve_document(rel_path):
    full_path = os.path.join(KB_DIR, rel_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None

def query_knowledge_base(keyword):
    idx = load_alias_index()
    kw = keyword.strip().lower()
    matches = idx.get(kw, [])
    results = []
    for m in matches:
        p = m['path']
        content = retrieve_document(p)
        results.append({
            'path': p,
            'desc': m.get('desc'),
            'content': content
        })
    return results

BENCHMARK_CASES = [
    {
        "id": "CASE_01_ELEANOR_PROFILE",
        "question": "埃莉诺的惯用武器叫什么？资历多长？出身哪个家族？",
        "lookup_keys": ["埃莉诺", "千藏"],
        "required_facts": [
            "千藏",
            "三个月",
            "菲茨罗伊"
        ]
    },
    {
        "id": "CASE_02_MAIN_STORY_BAD_END",
        "question": "主线第一章终局《没有旅人的未来》的官方跳过概要是什么？是哪个结局？",
        "lookup_keys": ["没有旅人的未来", "ch1"],
        "required_facts": [
            "多年后，你在沮丧中被人推进河里溺亡",
            "时间并不站在你们这边",
            "STm01_08_b"
        ]
    },
    {
        "id": "CASE_03_ELEANOR_ASCENSION",
        "question": "埃莉诺突破需要哪些专属材料？第3阶觉醒有什么特殊效果？",
        "lookup_keys": ["埃莉诺"],
        "required_facts": [
            "男爵的嘉赏",
            "男爵的窖藏",
            "男爵的恩典",
            "朵拉",
            "3 阶觉醒",
            "觉醒形态与立绘"
        ]
    },
    {
        "id": "CASE_04_ELEANOR_DATING",
        "question": "埃莉诺在甜品屋约会发生了什么？台词是什么？",
        "lookup_keys": ["埃莉诺", "大小姐的喂食"],
        "required_facts": [
            "大小姐的喂食",
            "甜品屋",
            "沉迷在了喂你吃东西的乐趣之中",
            "来，啊~张嘴"
        ]
    },
    {
        "id": "CASE_05_DISC_SKILL",
        "question": "唱片《朝霭》的主控技能名称和效果是什么？",
        "lookup_keys": ["朝霭"],
        "required_facts": [
            "强音·主调",
            "主控角色攻击力提升",
            "7%/8.4%/9.8%/11.2%/12.6%/14%"
        ]
    },
    {
        "id": "CASE_06_EMBLEM_AFFIX",
        "question": "Lv.70 纹章印记伤害 (Mark DMG) 的最高数值档位是多少？",
        "lookup_keys": ["纹章词条", "纹章"],
        "required_facts": [
            "Mark DMG",
            "80%",
            "34.35%"
        ]
    },
    {
        "id": "CASE_07_GAME_MODES",
        "question": "尖兵陷阵自走棋的队伍棋盘布局是什么？",
        "lookup_keys": ["尖兵陷阵", "自走棋"],
        "required_facts": [
            "3 主战 + 6 后援",
            "理智值",
            "贤才金币"
        ]
    },
    {
        "id": "CASE_08_EVENT_STORY",
        "question": "活动剧情《大小姐们的茶会》都有谁出场？",
        "lookup_keys": ["茶会", "大小姐们的茶会"],
        "required_facts": [
            "埃莉诺",
            "卡特琳",
            "薇薇安"
        ]
    }
]

def run_benchmark():
    print("=" * 60)
    print("RUNNING OFFLINE BENCHMARK ON WIKI KNOWLEDGE BASE")
    print("=" * 60)

    total = len(BENCHMARK_CASES)
    passed = 0

    for case in BENCHMARK_CASES:
        c_id = case['id']
        q = case['question']
        keys = case['lookup_keys']
        facts = case['required_facts']

        print(f"\n[{c_id}] Q: {q}")
        print(f"  Lookup keys: {keys}")

        # Collect documents retrieved
        retrieved_texts = []
        for k in keys:
            hits = query_knowledge_base(k)
            for h in hits:
                if h['content']:
                    retrieved_texts.append(h['content'])

        combined_text = "\n".join(retrieved_texts)
        missing_facts = []
        for fact in facts:
            if fact not in combined_text:
                missing_facts.append(fact)

        if not missing_facts:
            print(f"  [PASS] All {len(facts)} required factual items retrieved successfully!")
            passed += 1
        else:
            print(f"  [FAIL] Missing factual items: {missing_facts}")

    print("\n" + "=" * 60)
    print(f"BENCHMARK RESULT: {passed} / {total} PASSED ({passed / total * 100:.1f}%)")
    print("=" * 60)
    return passed == total

if __name__ == '__main__':
    success = run_benchmark()
    sys.exit(0 if success else 1)
