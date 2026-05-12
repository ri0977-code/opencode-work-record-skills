# OpenCode 工作记录技能包

工作记录自动读写 + 历史记忆搜索，让 OpenCode 拥有**持久记忆**。

## 包含的技能

### 1. work-record-reader

OpenCode 的工作记录系统——每次对话自动读取最新工作记录，结束时自动保存。配合定时备份和归档，实现项目进度的无缝衔接。

- 自动读取最近工作记录，恢复上下文
- 每小时自动备份（通过 Windows 计划任务）
- 月度/年度归档
- 跨天时段（00:00-00:59）智能处理
- 启动时自动检查并合并备份

### 2. opencode-memory-search

直接查询 opencode 的 SQLite 数据库，不依赖 recall API。支持全文搜索、会话回溯、时间过滤。

- 绕过 recall API 直接读本地 SQLite
- 全文关键词搜索
- 按时间范围过滤
- 按角色（user/assistant）过滤
- 无需服务器、无需网络

### 两者分工

| 技能 | 作用 | 数据源 |
|------|------|--------|
| `work-record-reader` | 今日进度、近期工作 | Markdown 工作记录文件 |
| `opencode-memory-search` | 历史全文检索，回溯任意对话 | opencode SQLite 数据库 |

## 安装

### 方式一：全局安装

```bash
# 将技能目录复制到 opencode 全局技能目录
cp -r skills/* ~/.config/opencode/skills/
```

Windows:

```cmd
xcopy /E /I skills\* %USERPROFILE%\.config\opencode\skills\
```

### 方式二：项目级安装

```bash
# 复制到项目的 .opencode/skills/ 目录
cp -r skills/* .opencode/skills/
```

## work-record-reader 额外配置

工作记录自动保存需要配合 Windows 计划任务使用。仓库中包含以下辅助脚本：

- `hourly_backup.py` — 每小时备份
- `archive.py` — 月度/年度归档
- `work_record_helper.py` — 检查状态、合并备份

详细配置请参考 `skills/work-record-reader/SKILL.md`。

## 文件结构

```
opencode-work-record-skills/
├── README.md
├── skills/
│   ├── work-record-reader/
│   │   └── SKILL.md
│   └── opencode-memory-search/
│       ├── SKILL.md
│       └── query_history.py
```

## 许可证

MIT
