---
name: opencode-memory-search
description: opencode 历史记忆全文搜索 - 直接查询 SQLite 数据库，不依赖 recall API。支持关键词搜索、会话回溯、时间过滤。
---

# opencode-memory-search — 历史记忆搜索

## 概述

opencode 内置的 `recall` 工具依赖服务器 API（端口 4096），需要 Basic Auth 凭据。
当服务器 API 不可用时，recall 完全失效。

本技能绕过 recall API，**直接读取本地的 SQLite 数据库**，提供比 recall 更强的搜索能力。

### 与 work-record-reader 的分工

| 技能 | 作用 | 数据源 |
|------|------|--------|
| `work-record-reader` | 今日进度、近期工作 | Markdown 工作记录文件 |
| `opencode-memory-search` | 历史全文检索，回溯任意对话 | opencode SQLite 数据库 |

两者互补：**工作记录记"结论"，SQLite 存"全过程"**。

---

## 何时激活

当用户提到以下情况时激活：

- "上次我们讨论过..."
- "帮我找一下关于 XX 的历史"
- "还记得之前安装 XX 的时候吗"
- "那天我们修了一个什么 bug"
- "以前有没有遇到过类似的问题"
- "recall 坏了，帮我查一下历史"
- "搜一下历史记录"

---

## 核心能力

### 1. 关键词搜索

```bash
python <skill_dir>/query_history.py search <关键词>
```

示例：
```
python query_history.py search PaddleOCR
→ 找到 295 条相关会话
  [04-28 14:22] PaddleOCR 安装配置讨论
  [05-09 10:15] PaddleOCR 版本问题排查
  ...
```

参数：
- `--limit N` — 返回条数（默认 5）
- `--days N` — 只搜最近 N 天

### 2. 查看完整会话

```bash
python <skill_dir>/query_history.py session <session_id>
```

显示整个会话的完整对话内容，包括角色、消息、工具调用。

### 3. 列出最近会话

```bash
python <skill_dir>/query_history.py list [--limit 20]
```

### 4. 查看统计

```bash
python <skill_dir>/query_history.py stats
```

---

## AI 行为规则

### 搜索流程

当用户询问历史时，AI 应按以下步骤操作：

```
1. 理解用户想找什么 → 提取关键词
2. 调用搜索脚本 → query_history.py search <关键词>
3. 根据结果：
   a. 如果找到相关会话 → 询问用户是否需要查看详情
   b. 如果需要完整内容 → query_history.py session <id>
   c. 如果没找到 → 提示用户换关键词，或查工作记录
4. 整合搜索结果到回答中
```

### 规则

- ✅ 先用关键词搜，再按需看详情
- ✅ 结合工作记录一起用（work-record-reader 提供最新进展，memory-search 提供历史上下文）
- ❌ 不要一次性 dump 整个会话内容（可能很长）
- ❌ 不要修改 SQLite 数据库（只读操作）
- ⚠️ 结果为空时，提醒用户换关键词试试

---

## 配套脚本

| 文件 | 作用 |
|------|------|
| `query_history.py` | SQLite 记忆查询主脚本 |

脚本位置：与 SKILL.md 同目录。

### 依赖

- Python 3（内置 sqlite3 模块，无需额外安装）

---

## 与 recall 的关系

| 对比 | recall 工具 | opencode-memory-search |
|------|-------------|----------------------|
| 数据源 | opencode server API | 本地 SQLite 数据库 |
| 依赖 | 服务器运行 + Basic Auth | 无依赖 |
| 搜索范围 | 摘要级别 | 全文搜索 |
| 可查看完整会话 | 有限 | ✅ 完整回溯 |
| 速度 | 快（摘要） | 中等（全表扫描） |
| 关键词搜索 | 支持 | 支持更精确 |
| 当前状态 | ❌ 401 Unauthorized | ✅ 可用 |

---

## 故障排除

### "数据库不存在"
- 检查 `~/.local/share/opencode/opencode.db` 是否存在
- 需要至少运行过一次 opencode

### 搜索太慢
- 数据库超过 10 万条消息时，全表扫描会变慢
- 可以用 `--days` 限制搜索范围
- 后续可考虑加入 FTS5 全文索引优化

### "找不到相关内容"
- 换更短的关键词再试
- 检查是否在正确的目录下（本技能只查 C:\ 根目录的会话）
- 结合工作记录文件查找
