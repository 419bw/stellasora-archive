# -*- coding: utf-8 -*-
"""剧本域常量：文本清洗与说话人解析等 pass 共用的官方设定。

原为 build_story.py 模块级常量（PROTAG_ID/PROTAG_NAME），随语义 pass
拆入管线（Phase 1c），值与官方 AvgCharacter 预设口径一致，不得擅改——
改动会改变台词行的说话人显示与主角占位符替换结果（黄金对拍会红）。
"""

# 主角的 AVG 说话人 id 集合（含性别/形态变体与通用占位 "1"）
PROTAG_ID = ("avg3_100", "avg3_101", "avg3_1311", "avg3_1312", "1")
# 主角显示名（==PLAYER_NAME== 占位符的替换目标）
PROTAG_NAME = "魔王"
