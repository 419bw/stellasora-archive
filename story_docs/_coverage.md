# 剧本覆盖对账

- 包内 AVG 剧本：626　已渲染：552　未渲染：74

| 剧本前缀 | 文件数 | 已渲染 | 未渲染 | 挂载来源 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `STm_*` | 180 | 180 | 0 | Story.AvgLuaName | 含序章 STm00_*，已渲染进 prologue/ |
| `CG_*` | 156 | 156 | 0 | Plot / NPCAffinityPlot / DiscIP |  |
| `STev_*` | 105 | 105 | 0 | ActivityStory.AvgLuaName |  |
| `PM_*` | 73 | 0 | 73 | Chat.AVGId | 心链聊天全篇，已提取至 `_chat/` 人读存档（不进站点，故不计入已渲染） |
| `STsp_*` | 56 | 56 | 0 | StorySetSection.AVGId |  |
| `BBm_*` | 35 | 35 | 0 | 无表引用，客户端按「关卡代号里的章号+关卡编号」拼名 | 战斗气泡，含 7 个无表引用者（序章一战 + 第七章追加战） |
| `DP_*` | 18 | 18 | 0 | AgentSpecialPerformance.Avg | 委托结算演出，已入 dispatch/（按结算演出段收录，见 _dev 手册 7.4） |
| `ST_*` | 2 | 2 | 0 | ActivityReturnee.AVG（ST_sys_reengagement）；ST_sys_soldier_intro 无表引用 | ST_sys_* 系统流程剧本：回归活动《归星漫途》入 returnee/，尖兵陷阵开场入 soldier/ |
| `GD_*` | 1 | 0 | 1 | 无表引用 | 抽卡演出小段（4 句），表不引用，待决 |

## 未渲染剧本清单

- `GD_gacha`（挂载表：无）
- `PM10301`（挂载表：Chat）
- `PM10302`（挂载表：Chat）
- `PM10701`（挂载表：Chat）
- `PM10702`（挂载表：Chat）
- `PM10801`（挂载表：Chat）
- `PM10802`（挂载表：Chat）
- `PM11001`（挂载表：Chat）
- `PM11002`（挂载表：Chat）
- `PM11101`（挂载表：Chat）
- `PM11102`（挂载表：Chat）
- `PM11201`（挂载表：Chat）
- `PM11202`（挂载表：Chat）
- `PM11301`（挂载表：Chat）
- `PM11302`（挂载表：Chat）
- `PM11401`（挂载表：Chat）
- `PM11501`（挂载表：Chat）
- `PM11601`（挂载表：Chat）
- `PM11602`（挂载表：Chat）
- `PM11701`（挂载表：Chat）
- `PM11702`（挂载表：Chat）
- `PM11801`（挂载表：Chat）
- `PM11802`（挂载表：Chat）
- `PM11901`（挂载表：Chat）
- `PM11902`（挂载表：Chat）
- `PM12001`（挂载表：Chat）
- `PM12002`（挂载表：Chat）
- `PM12301`（挂载表：Chat）
- `PM12302`（挂载表：Chat）
- `PM12501`（挂载表：Chat）
- `PM12502`（挂载表：Chat）
- `PM12601`（挂载表：Chat）
- `PM12602`（挂载表：Chat）
- `PM12701`（挂载表：Chat）
- `PM12702`（挂载表：Chat）
- `PM13001`（挂载表：Chat）
- `PM13002`（挂载表：Chat）
- `PM13201`（挂载表：Chat）
- `PM13202`（挂载表：Chat）
- `PM13301`（挂载表：Chat）
- `PM13302`（挂载表：Chat）
- `PM13401`（挂载表：Chat）
- `PM13402`（挂载表：Chat）
- `PM13501`（挂载表：Chat）
- `PM13502`（挂载表：Chat）
- `PM13701`（挂载表：Chat）
- `PM13901`（挂载表：Chat）
- `PM14001`（挂载表：Chat）
- `PM14101`（挂载表：Chat）
- `PM14102`（挂载表：Chat）
- `PM14201`（挂载表：Chat）
- `PM14202`（挂载表：Chat）
- `PM14301`（挂载表：Chat）
- `PM14302`（挂载表：Chat）
- `PM14401`（挂载表：Chat）
- `PM14402`（挂载表：Chat）
- `PM14501`（挂载表：Chat）
- `PM14701`（挂载表：Chat）
- `PM14702`（挂载表：Chat）
- `PM14901`（挂载表：Chat）
- `PM14902`（挂载表：Chat）
- `PM15001`（挂载表：Chat）
- `PM15002`（挂载表：Chat）
- `PM15501`（挂载表：Chat）
- `PM15502`（挂载表：Chat）
- `PM15601`（挂载表：Chat）
- `PM15602`（挂载表：Chat）
- `PM15701`（挂载表：Chat）
- `PM15801`（挂载表：Chat）
- `PM15802`（挂载表：Chat）
- `PM15901`（挂载表：Chat）
- `PM15902`（挂载表：Chat）
- `PM16001`（挂载表：Chat）
- `PM16201`（挂载表：Chat）
