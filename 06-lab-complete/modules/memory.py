"""
Memory Module — Session and persistent memory using SQLite.
Stores conversation history, chart iterations, user preferences,
and provides context injection for the Orchestrator.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import config


class MemoryModule:
    """SQLite-backed memory for sessions, charts, conversations, and preferences."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(config.DATABASE_PATH)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    active_dataset_path TEXT,
                    active_dataset_schema TEXT,
                    status TEXT DEFAULT 'active'
                );

                CREATE TABLE IF NOT EXISTS charts (
                    chart_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    iteration INTEGER DEFAULT 1,
                    chart_config TEXT,
                    code TEXT,
                    image_path TEXT,
                    insights TEXT,
                    created_at TEXT NOT NULL,
                    user_feedback TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, key),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Session Management ──────────────────────────────────────

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, created_at, last_active) VALUES (?, ?, ?)",
                (session_id, now, now),
            )
        return session_id

    def get_or_create_session(self, session_id: str = None) -> str:
        """Get existing session or create a new one."""
        if session_id:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT session_id FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if row:
                    conn.execute(
                        "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                        (datetime.now().isoformat(), session_id),
                    )
                    return session_id
        return self.create_session()

    def update_active_dataset(self, session_id: str, file_path: str, schema_json: str):
        """Update the active dataset for a session."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE sessions SET active_dataset_path = ?, active_dataset_schema = ?, last_active = ? WHERE session_id = ?",
                (file_path, schema_json, datetime.now().isoformat(), session_id),
            )

    def get_active_dataset(self, session_id: str) -> dict:
        """Get the active dataset info for a session."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT active_dataset_path, active_dataset_schema FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row and row["active_dataset_path"]:
                schema = json.loads(row["active_dataset_schema"]) if row["active_dataset_schema"] else None
                return {"path": row["active_dataset_path"], "schema": schema}
        return None

    # ── Chart History ───────────────────────────────────────────

    def save_chart(self, session_id: str, chart_config: dict, code: str,
                   image_path: str, insights: str = "") -> str:
        """Save a chart iteration and return its ID."""
        chart_id = f"chart_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()

        # Get current iteration number
        with self._connect() as conn:
            row = conn.execute(
                "SELECT MAX(iteration) as max_iter FROM charts WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            iteration = (row["max_iter"] or 0) + 1

            conn.execute(
                """INSERT INTO charts (chart_id, session_id, iteration, chart_config, code, image_path, insights, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (chart_id, session_id, iteration,
                 json.dumps(chart_config, ensure_ascii=False),
                 code, image_path, insights, now),
            )

        return chart_id

    def get_current_chart(self, session_id: str) -> dict:
        """Get the most recent chart for a session."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM charts WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if row:
                return self._chart_row_to_dict(row)
        return None

    def get_chart_by_id(self, chart_id: str) -> dict:
        """Get a specific chart by ID."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM charts WHERE chart_id = ?",
                (chart_id,),
            ).fetchone()
            if row:
                return self._chart_row_to_dict(row)
        return None

    def get_chart_history(self, session_id: str, last_n: int = 10) -> list:
        """Get recent chart history for a session."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM charts WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, last_n),
            ).fetchall()
            return [self._chart_row_to_dict(r) for r in rows]

    def _chart_row_to_dict(self, row) -> dict:
        """Convert a chart database row to a dictionary."""
        return {
            "chart_id": row["chart_id"],
            "session_id": row["session_id"],
            "iteration": row["iteration"],
            "chart_config": json.loads(row["chart_config"]) if row["chart_config"] else {},
            "code": row["code"],
            "image_path": row["image_path"],
            "insights": row["insights"],
            "created_at": row["created_at"],
            "user_feedback": row["user_feedback"],
        }

    # ── Conversation History ────────────────────────────────────

    def save_conversation_turn(self, session_id: str, role: str, content: str, metadata: dict = None):
        """Save a conversation turn."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, content, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, datetime.now().isoformat(),
                 json.dumps(metadata, ensure_ascii=False) if metadata else None),
            )

    def get_conversation_history(self, session_id: str, last_n: int = 20) -> list:
        """Get recent conversation history."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, last_n),
            ).fetchall()
            return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in reversed(rows)]

    def get_conversation_summary(self, session_id: str, last_n: int = 10) -> str:
        """Get a text summary of recent conversation."""
        history = self.get_conversation_history(session_id, last_n)
        if not history:
            return "No conversation history."
        lines = []
        for turn in history:
            role_label = "👤 User" if turn["role"] == "user" else "🤖 Agent"
            # Truncate long messages
            content = turn["content"][:200] + "..." if len(turn["content"]) > 200 else turn["content"]
            lines.append(f"{role_label}: {content}")
        return "\n".join(lines)

    # ── User Preferences ────────────────────────────────────────

    def learn_preference(self, session_id: str, key: str, value: str):
        """Store or update a user preference."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO preferences (session_id, key, value, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, key, value, datetime.now().isoformat()),
            )

    def get_preferences(self, session_id: str) -> dict:
        """Get all preferences for a session."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT key, value FROM preferences WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            return {r["key"]: r["value"] for r in rows}

    # ── Context Assembly ────────────────────────────────────────

    def get_current_context(self, session_id: str) -> dict:
        """
        Assemble the full context for the Orchestrator.
        This is injected into the LLM prompt for context awareness.
        """
        active_dataset = self.get_active_dataset(session_id)
        current_chart = self.get_current_chart(session_id)
        chart_history = self.get_chart_history(session_id, last_n=5)
        preferences = self.get_preferences(session_id)
        conversation = self.get_conversation_summary(session_id, last_n=5)

        return {
            "active_dataset": active_dataset,
            "current_chart": current_chart,
            "chart_history_count": len(chart_history),
            "chart_history": [
                {"chart_id": c["chart_id"], "iteration": c["iteration"],
                 "chart_type": c["chart_config"].get("chart_type", "unknown"),
                 "title": c["chart_config"].get("title", ""),
                 "created_at": c["created_at"]}
                for c in chart_history
            ],
            "user_preferences": preferences,
            "recent_conversation": conversation,
        }

    def get_context_text(self, session_id: str) -> str:
        """Get context as a formatted text string for LLM injection."""
        ctx = self.get_current_context(session_id)

        lines = ["[CURRENT CONTEXT]"]

        # Dataset info
        if ctx["active_dataset"]:
            schema = ctx["active_dataset"].get("schema", {})
            if schema:
                lines.append(f"Dataset: {schema.get('filename', 'unknown')} "
                           f"({schema.get('row_count', '?')} rows × {schema.get('col_count', '?')} cols)")
                cols = schema.get("columns", [])
                if cols:
                    col_summary = ", ".join([f"{c['name']}({c['medical_role']})" for c in cols[:8]])
                    lines.append(f"Columns: {col_summary}")
        else:
            lines.append("Dataset: None loaded")

        # Current chart
        if ctx["current_chart"]:
            cc = ctx["current_chart"]
            lines.append(f"Current chart: {cc['chart_config'].get('chart_type', '?')} — "
                        f"{cc['chart_config'].get('title', 'untitled')} (#{cc['iteration']})")
        else:
            lines.append("Current chart: None")

        # History
        if ctx["chart_history_count"] > 0:
            lines.append(f"Chart history: {ctx['chart_history_count']} charts in this session")

        # Preferences
        if ctx["user_preferences"]:
            prefs = ", ".join([f"{k}={v}" for k, v in ctx["user_preferences"].items()])
            lines.append(f"User preferences: {prefs}")

        return "\n".join(lines)

    # ── Cleanup ─────────────────────────────────────────────────

    def clear_session(self, session_id: str):
        """Clear all data for a session."""
        with self._connect() as conn:
            conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM charts WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM preferences WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
