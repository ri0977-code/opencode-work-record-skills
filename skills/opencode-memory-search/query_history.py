"""
opencode 历史记忆查询工具
直接从 SQLite 数据库读取历史会话，不依赖 recall API。

用法：
    python query_history.py search <关键词>                   # 关键词搜索
    python query_history.py search <关键词> --limit 10        # 指定返回条数
    python query_history.py search <关键词> --days 7          # 只搜最近7天
    python query_history.py session <session_id>              # 查看完整会话
    python query_history.py list                              # 列出最近会话
    python query_history.py stats                             # 统计信息
"""
import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser(
    r"~\.local\share\opencode\opencode.db"
)


def get_conn():
    if not os.path.exists(DB_PATH):
        print(f"[ER] 数据库不存在: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def search(keyword, limit=5, days=None):
    """搜索历史对话"""
    conn = get_conn()
    cur = conn.cursor()

    # 搜索消息中的文本内容
    sql = """
        SELECT DISTINCT m.session_id, p.data, m.time_created
        FROM message m
        JOIN part p ON p.message_id = m.id AND p.session_id = m.session_id
        WHERE p.data LIKE ?
    """
    params = [f"%{keyword}%"]

    if days:
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        sql += " AND m.time_created > ?"
        params.append(cutoff)

    sql += " ORDER BY m.time_created DESC LIMIT ?"
    params.append(limit * 3)  # 多取一些以便去重

    rows = cur.execute(sql, params).fetchall()

    # 去重并按会话分组
    sessions = {}
    for s_id, pdata_json, ts in rows:
        if s_id not in sessions and len(sessions) < limit:
            pd = json.loads(pdata_json)
            if pd.get("type") == "text":
                sessions[s_id] = {
                    "session_id": s_id,
                    "text": pd.get("text", ""),
                    "time": ts,
                }

    # 获取会话标题
    for sid in sessions:
        title_row = conn.execute(
            "SELECT title, model FROM session WHERE id = ?", (sid,)
        ).fetchone()
        if title_row:
            sessions[sid]["title"] = title_row[0]
            model_data = title_row[1]
            if model_data:
                try:
                    sessions[sid]["model"] = json.loads(model_data).get("id", "?")
                except:
                    sessions[sid]["model"] = "?"
            else:
                sessions[sid]["model"] = "built-in"
        else:
            sessions[sid]["title"] = "(无标题)"
            sessions[sid]["model"] = "?"

        # 格式化时间
        ts_ms = sessions[sid]["time"]
        if ts_ms:
            dt = datetime.fromtimestamp(ts_ms / 1000)
            sessions[sid]["time_str"] = dt.strftime("%m-%d %H:%M")
        else:
            sessions[sid]["time_str"] = "?"

    conn.close()
    return list(sessions.values())


def view_session(session_id):
    """查看完整会话内容"""
    conn = get_conn()
    cur = conn.cursor()

    # 获取会话信息
    session = cur.execute(
        "SELECT id, title, directory, time_created, model FROM session WHERE id = ?",
        (session_id,),
    ).fetchone()
    if not session:
        print(f"[ER] 未找到会话: {session_id}")
        return

    print(f"===== 会话: {session[1] or '(无标题)'} =====")
    print(f"ID: {session[0]}")
    print(f"目录: {session[2]}")
    if session[4]:
        try:
            print(f"模型: {json.loads(session[4]).get('id', '?')}")
        except:
            print(f"模型: ?")
    dt = datetime.fromtimestamp(session[3] / 1000) if session[3] else None
    print(f"时间: {dt.strftime('%Y-%m-%d %H:%M') if dt else '?'}")
    print()

    # 获取消息
    msgs = cur.execute(
        """
        SELECT m.id, m.data, m.time_created
        FROM message m
        WHERE m.session_id = ?
        ORDER BY m.time_created ASC
        """,
        (session_id,),
    ).fetchall()

    for m_id, mdata_json, ts in msgs:
        mdata = json.loads(mdata_json)
        role = mdata.get("role", "?")
        parts = cur.execute(
            "SELECT data FROM part WHERE message_id = ? AND session_id = ? ORDER BY time_created ASC",
            (m_id, session_id),
        ).fetchall()

        text_parts = []
        for p in parts:
            pd = json.loads(p[0])
            if pd.get("type") == "text":
                text_parts.append(pd.get("text", ""))
            elif pd.get("type") == "tool":
                t = pd.get("tool", "")
                desc = ""
                state = pd.get("state", {})
                if isinstance(state, dict):
                    desc = state.get("metadata", {}).get("description", "")
                text_parts.append(f"[工具: {t} {desc}]".strip())

        content = " | ".join(text_parts)
        if content:
            print(f"[{role}] {content[:500]}")

    conn.close()


def list_sessions(limit=10):
    """列出最近会话"""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, title, time_created, model
        FROM session
        ORDER BY time_created DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    print(f"最近 {len(rows)} 个会话:\n")
    for sid, title, ts, model_data in rows:
        dt = datetime.fromtimestamp(ts / 1000) if ts else None
        time_str = dt.strftime("%m-%d %H:%M") if dt else "?"
        model = "?"
        if model_data:
            try:
                model = json.loads(model_data).get("id", "?")
            except:
                pass
        title_clean = (title or "(无标题)").replace("\n", " ")
        print(f"  {time_str} | {model[:20]:20s} | {sid[:25]:25s} | {title_clean[:40]}")


def stats():
    """统计信息"""
    conn = get_conn()
    session_count = conn.execute("SELECT COUNT(*) FROM session").fetchone()[0]
    msg_count = conn.execute("SELECT COUNT(*) FROM message").fetchone()[0]
    part_count = conn.execute("SELECT COUNT(*) FROM part").fetchone()[0]
    # 最早和最晚的会话
    earliest = conn.execute(
        "SELECT MIN(time_created) FROM session"
    ).fetchone()[0]
    latest = conn.execute("SELECT MAX(time_created) FROM session").fetchone()[0]
    conn.close()

    def ts_to_str(ts):
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d") if ts else "?"

    print(f"opencode 记忆数据库统计:\n")
    print(f"  会话数:     {session_count}")
    print(f"  消息数:     {msg_count}")
    print(f"  片段数:     {part_count}")
    print(f"  最早会话:   {ts_to_str(earliest)}")
    print(f"  最近会话:   {ts_to_str(latest)}")
    print(f"  数据库路径: {DB_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "search":
        if len(sys.argv) < 3:
            print("用法: python query_history.py search <关键词> [--limit N] [--days N]")
            sys.exit(1)
        keyword = sys.argv[2]
        limit = 5
        days = None
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])
        if "--days" in sys.argv:
            idx = sys.argv.index("--days")
            days = int(sys.argv[idx + 1])
        results = search(keyword, limit, days)
        if not results:
            print(f"[..] 未找到包含 \"{keyword}\" 的历史记录")
        else:
            print(f"找到 {len(results)} 条相关会话:\n")
            for r in results:
                title = r["title"] or "(无标题)"
                print(f"  [{r['time_str']}] [{r['model']}] {title}")
                print(f"  会话ID: {r['session_id']}")
                text = r["text"].replace("\n", " ")[:120]
                print(f"  内容: {text}...")
                print()

    elif command == "session":
        if len(sys.argv) < 3:
            print("用法: python query_history.py session <session_id>")
            sys.exit(1)
        view_session(sys.argv[2])

    elif command == "list":
        limit = 10
        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            limit = int(sys.argv[idx + 1])
        list_sessions(limit)

    elif command == "stats":
        stats()

    else:
        print(f"未知命令: {command}")
        print(__doc__)
