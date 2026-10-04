# 《星塔旅人》剧情档案 (Stella Sora Archive)

在线访问：[https://stellasora-archive.pages.dev/](https://stellasora-archive.pages.dev/)  
开源仓库：[https://github.com/419bw/stellasora-archive](https://github.com/419bw/stellasora-archive)

---

## 阅读提示与剧透预警

> **剧透预警**：本档案库默认完整展开所有主线及活动剧情的全部交互抉择、分支路线与多重结局，包含全流程剧透。尚未通关或希望亲自探索剧情的玩家建议谨慎查阅。
> 
> **收录范围说明**：游戏内仅有 CG 动画演示而无台词字幕的纯过场片段，不包含在官方剧本配置中，因此不会收录在站内。本站专注于完整收录官方数据源中包含对白文本、角色内心独白、分支选项与战斗气泡的剧情内容。

---

## 档案库收录内容

本站收录公测版本以来的全量文本与分支剧情：

- **主线全章节（含特别篇）**：主线各章节及特别篇《谜影的序曲》，还原官方游戏内交互式拓扑连线图，支持分支抉择、多结局推演与纯战斗档案。
- **活动剧情**：各期主题活动的关卡剧情全文与阶段收录，支持活动专属分支拓扑。
- **角色个人剧情**：旅人专属故事，好感等级逐级解锁的专属剧情全文本。
- **星塔 NPC 羁绊**：星塔驻留人员与常驻 NPC 的日常好感羁绊剧情。
- **秘闻**：收录秘闻剧本与官方原版散文、故事集日常回忆与侧写。
- **战场气泡与战斗档案**：随战斗阶段推进的角色实时气泡对白，以及零对白战斗关卡的独立档案与流程跳转。

---

## 快速使用与本地预览

### 方式一：直接双击打开（完全离线）
进入 `site/` 目录，直接用浏览器双击打开 [`site/index.html`](./site/index.html) 即可开始浏览与检索（搜索已做本地离线静态内嵌，无需网络支持）。

### 方式二：本地 HTTP 服务预览（推荐）
在项目根目录下运行 Python 内置服务器：
```bash
python -m http.server 8000 --directory site
```
然后在浏览器中访问：`http://localhost:8000`

### 方式三：从源码重新构建
```bash
# 1. 从数据源重新解析并生成 Markdown 与拓扑侧车
python scripts/story/build_story.py

# 2. 编译全量静态网页
python scripts/site/build_site.py

# 3. 运行自动化契约校验（确保 0 漂移与 0 违例）
python tests/story/validate_site.py
```

---

## 自动化同步与持续部署 (CI/CD)

本项目配置了完整的 GitHub Actions 持续集成与部署工作流（`.github/workflows/deploy.yml`）：
- **定时监控**：每 6 小时自动比对上游数据镜像仓库的最新提交。
- **自动同步与构建**：发现上游数据更新时，自动提取更新差异、重新构建剧本库与静态站点，并通过所有断言测试。
- **自动部署**：构建完成后自动推送到 Cloudflare Pages 全球边缘网络，确保在线网站与游戏更新保持同步。

---

## 免责声明 (Disclaimer)

1. **非官方非关联声明**：本站为玩家自制的非官方资料整理工具，与游戏官方运营团队无任何关联。
2. **知识产权与版权归属**：YOSTAR GAMES（悠星网络）拥有游戏的原始资产，站内涉及的游戏文案、剧本、立绘、头像、图标等素材版权均归原发行商及原版权方所有。
3. **交流学习与非盈利用途**：本站仅供剧情研读、世界观考据与个人交流学习使用，100% 为非盈利性粉丝项目，不以任何形式盈利，不提供素材下载与游戏客户端修改。如因使用相关内容产生任何争议或损失，本站概不负责。
4. **侵权反馈与联系**：若官方团队或版权所有方认为本站收录内容有所不妥，请联系维护者邮箱 `1950537289@qq.com`，我们将第一时间配合调整或删除。

---

## 数据来源与上游鸣谢 (Upstream Data Sources)

本档案库的高保真内容生成依赖社区开源维护的数据镜像。在此向以下优秀的上游开源项目致以诚挚谢意：

- **[StellaSoraData](https://github.com/AutumnVN/StellaSoraData)**（由 AutumnVN 维护）：提供全量官方结构化数据配置（关卡、章节、好感与活动表）及官方中文文案查找表。
- **[ss-lua](https://github.com/MakoStar/ss-lua)**（由 MakoStar 维护）：提供全量反编译 AVG 剧情脚本（`Avg/_cn/Config/*.lua`）与角色预设查找表（`AvgCharacter.lua`），使本项目能精准还原逐句对话、内心独白与分支抉择。

---

## 开发者与维护文档

- [操作与更新手册 (OPERATION_MANUAL.md)](./OPERATION_MANUAL.md)：数据源规范、脚本体系说明与版本维护流程。
- [底层逆向与交接指南 (AI_HANDOVER_GUIDE.md)](./AI_HANDOVER_GUIDE.md)：状态机设计、三类抉择项清洗标准、图拓扑算法与地面真实验证契约。

---

## 最近更新记录

### 2026-10-04
- feat(automation): 修复自动更新日志未生效，新增 push 触发的提交驱动日志

---

## 项目架构与脚本目录

项目采用清晰的职责分层架构：

```
stellasora-archive/
├── story_docs/              # Markdown 真源文档库与结构化侧车数据
│   └── _data/               # chapters.json, sections.json, search.json 等
├── scripts/                 # 构建与维护脚本工具集
│   ├── story/               # 剧情抽取与拓扑计算模块
│   │   ├── build_story.py   # 解析官方数据源 -> 生成 Markdown 与侧车数据
│   │   └── graph_layout.py  # DAG 分层拓扑几何纯函数（坐标与连线计算）
│   ├── site/                # 静态站点生成引擎
│   │   ├── build_site.py    # 驱动模板生成 549 篇 HTML 静态页面
│   │   ├── site_templates.py# 拓扑图、剧情阅读牌板、战斗档案等页面模板
│   │   ├── site_css.py      # 设计规范 Tokens 与全局样式
│   │   ├── site_js.py       # 离线检索、拓扑图手势交互等前端脚本
│   │   └── md2html.py       # Markdown 与 Ruby 注音原生转换器
│   ├── automation/          # 自动化持续集成模块
│   │   └── auto_sync.py     # 自动化上游数据对比、增量同步与 CI 发版
│   └── tools/               # 辅助与基准测试工具
│       ├── run_benchmark.py # 耗时与解析性能基准压测
│       └── build_wiki.py    # 早期原型抽取脚本
├── site/                    # 编译输出目录（供本地查阅或托管平台直接部署）
├── tests/story/             # 地面真相严格契约与变异测试套件 (A-K 组测试)
└── .github/workflows/       # GitHub Actions 自动化构建与定时同步流水线
```

> 提示：在 `scripts/` 根目录下提供了 `build_site.py`、`build_story.py` 与 `auto_sync.py` 的轻量转发器，直接在根目录执行旧命令依然 100% 兼容。
