> 《AI 技术交接手册》第 一、二 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 一、 数据源层：开源数据规范与镜像结构

本项目为保证代码合规性与长效免维护，**不包含任何客户端二进制逆向破解或客户端解密代码与密钥**。数据源完全依托开源社区维护的标准化结构镜像仓库，直接从结构化数据中消费提取：

### 1.1 开源数据源仓库架构
本项目的提取管道消费以下两个公开仓库的数据结构：
1. **结构化数据配置库**（如 `StellaSoraData`）：
   - `CN/bin/Story.json`：关卡列表
   - `CN/bin/StoryChapter.json`：章节列表
   - `CN/bin/ActivityStory.json`：活动剧情关卡
   - `CN/bin/DatingCharacterEvent.json`：旅人约会剧情
   - `CN/language/zh_CN/*.json`：全量官方中文字符串查找表
2. **文本剧本库**（如 `ss_lua`）：
   - `Lua/Game/UI/Avg/_cn/Config/*.lua`：所有剧本源码（如 `STm01_01.lua`, `STm02_01.lua`）
   - `Lua/Game/UI/Avg/_cn/Preset/AvgCharacter.lua`：说话人 ID 与姓名对应表
   - `Lua/Game/UI/Avg/AvgCmdParamOptionDefine.lua`：AVG 引擎参数枚举定义（包含 `TalkType`）

---

## 二、 数据结构与映射关系规范

在生成任何剧情文档前，必须理清这三张核心表之间的关系：

```text
StoryChapter.json (章节定义)
   └── Id (如 1, 2, 3...)
        └── Story.json (关卡节点定义)
             ├── Id (关卡主键, 如 204)
             ├── Index (国际化Key, 如 "Story.204.4" -> "01")
             ├── Title (国际化Key, 如 "Story.204.1" -> "公司与绿洲")
             ├── Desc (关卡描述句/一句话提示, 如 "Story.204.2" -> "从天而降的好处越多，就越要谨慎行事。")
             │        注意：这不是跳过概要！跳过概要在剧本的 SetIntro 第 4 个参数里（见 7.2 表）
             ├── Aim (通关目标Key, 如 "Story.204.3")
             ├── IsBattle (是否战斗关: true / false)
             ├── ParentStoryId (前置依赖关卡数组, 如 ["STm02_01"])
             └── AvgLuaName (对应的剧本文件名, 如 "STm02_01")
                  └── Avg/_cn/Config/STm02_01.lua (具体的逐句台词执行流)
```

> **注意**：文本绝不能直接硬编码，除 `AvgLuaName` 里的台词在 Lua 中外，关卡标题、通关目标、默认描述都在 `CN/language/zh_CN/Story.json` 里通过 Key 索引。
