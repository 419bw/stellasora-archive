> 《AI 技术交接手册》第 四 章正文分册；总索引与「按需索取」表见 [AI_HANDOVER_GUIDE.md](../AI_HANDOVER_GUIDE.md)。章节编号沿用原书，跨章引用（如「见 3.6」）按索引定位。

## 四、 拓扑图构建算法（Mermaid DAG）

主线剧情包含大量的分支抉择与支线结局（如 Bad End、提前终局）。必须通过每关的 `ParentStoryId` 字段构建依赖树，避免把非线性剧情排成一条单链。

### 核心构建逻辑
```python
# 1. 建立 code -> 标题/节点的映射
code_to_node = {}
for s in chap_sections:
    s_code = s.get('StoryId')
    s_idx = clean_text(lang_story.get(s.get('Index', ''), ''))
    s_title = clean_text(lang_story.get(s.get('Title', ''), ''))
    code_to_node[s_code] = f"{s_idx}_{s_title}"

# 2. 遍历依赖关系生成连线
edges = []
for s in chap_sections:
    current_code = s.get('StoryId')
    current_name = code_to_node.get(current_code)
    parents = s.get('ParentStoryId', [])
    for p in parents:
        parent_name = code_to_node.get(p)
        if parent_name and current_name:
            edges.append(f"    {parent_name}[\"{parent_name}\"] --> {current_name}[\"{current_name}\"]")

# 3. 渲染为标准 Mermaid
mermaid_doc = "```mermaid\ngraph LR\n" + "\n".join(edges) + "\n```"
```
