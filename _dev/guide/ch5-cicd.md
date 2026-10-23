> 《AI 技术交接手册》第 五 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 五、 自动化持续集成流水线（CI/CD）

工作流定义在 `.github/workflows/deploy.yml`，三种触发方式走**两条不同的路**：

| 触发 | 步骤 |
|---|---|
| `push`（推送到 `main`） | 收集提交生成更新日志 → **全量单元测试** `pytest tests/story tests/automation -q` → `validate_story.py`（含诊断侧车的重建漂移检查）→ 构建静态站 → `validate_site.py` → 提交生成物 → 部署 Cloudflare Pages |
| `schedule`（每 6 小时） | 跑 `scripts/automation/auto_sync.py`：比对两个上游仓库最新提交 → 有更新则重建 `story_docs/` + `site/` → 跑校验 → 提交（`[skip ci]`）→ 部署 |
| `workflow_dispatch` | 同 `schedule`，额外支持 `force_sync`（上游没变也强制）、`allow_single_upstream`（任一上游更新即同步）、`changelog_note`（手动指定更新理由） |

**几条关键语义**：

- **`auto_sync.py` 以 `check=True` 运行生成器**，所以生成器任何未捕获异常都会让整条定时同步停摆。
  管线的对应方针是"降级不崩 + 必登记"，见 3.6。
- **单元测试必须全量**。历史上 CI 只跑 `test_release_gate.py` + `test_changelog.py`，
  导致新增的测试文件在流水线里等于没测；2026-10-10 起改为 `pytest tests/story tests/automation -q`。
  新增测试文件时不需要改 workflow，但**别再把列表改回白名单**。
- **本地快循环 ≠ CI 白名单**：全量语料级集成用例（596 剧本条件解析、全侧车 markup 往返、
  eager-reads 审计）带 `@pytest.mark.slow`（注册于根 `pytest.ini`），本地日常改动可跑
  `pytest -m "not slow"`（秒级）；CI 与验收仍然全量，上一条纪律不受影响。
  共享 DataContext 走 `tests/conftest.py` 的 session 级 `data_ctx` fixture（惰性构造），
  但 eager-reads 审计必须构造新鲜实例（共享实例会被懒读污染 `resolved_tables()`）。
- **`story_docs/` 是提交物**：定时同步重建后会 `git add story_docs/` 提交，所以上游数据一变，
  diff 里能直接看到新增/变化的页面与 `_diagnostics.json` 的新登记——这是发现上游结构变动的主渠道。
- **部署是纯静态目录** `site/`，用 Cloudflare Pages（项目名 `stellasora-archive`）。
  换任何静态托管都行，构建产物不依赖平台。
- `STELLA_DIAG_REBUILD=0` 可跳过诊断侧车的子进程重建（省一次全量 build），默认开启。
