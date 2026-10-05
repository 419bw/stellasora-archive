# -*- coding: utf-8 -*-
"""管线 Stage 3b: 说话人解析 —— AVG 说话人 id → 显示名。

自 build_story.py 的 speaker_of/speaker_prefix_of 原样迁出（Phase 1c），
逐行为等价。SPEAKERS 映射（id → (name, surfix)）来自官方 AvgCharacter.lua
预设，由宿主注入，本模块不碰文件系统。
"""
from .domain import PROTAG_ID, PROTAG_NAME
from .text_rules import clean_text


class SpeakerResolver:
    """Resolve an AVG speaker id to a display name, honouring the protagonist rules."""

    def __init__(self, speakers):
        self.speakers = speakers    # id -> (name, surfix)

    def of(self, spk_id, talk_type):
        sid = str(spk_id)
        if sid in PROTAG_ID:
            return PROTAG_NAME
        if sid == "0":
            return PROTAG_NAME if str(talk_type) == "2" else "旁白"
        name, surfix = self.speakers.get(sid) or self.prefix_of(sid) or ("", "")
        return clean_text(name or surfix or sid)

    def prefix_of(self, sid):
        """Variant speaker keys carry a suffix the preset table does not list (avg1_144_BB_002
        is 千都世), so fall back to the longest dotted prefix that is registered."""
        parts = sid.split('_')
        for cut in range(len(parts) - 1, 1, -1):
            hit = self.speakers.get('_'.join(parts[:cut]))
            if hit:
                return hit
        return None
