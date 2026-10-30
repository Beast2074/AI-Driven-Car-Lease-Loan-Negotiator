"""
Secure Audit Logger Service
Logs all system actions (uploads, analyses, VIN lookups, comparisons, chats, errors).
Restricted access: only accessible via ADMIN_SECRET_KEY.
"""

import os
import json
import sqlite3
import logging
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "12345")
BASE_TEMP = tempfile.gettempdir()
LOG_DIR = os.getenv("LOG_DIR", os.path.join(BASE_TEMP, "logs"))
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except Exception:
    pass
AUDIT_FILE = os.path.join(LOG_DIR, "audit.jsonl")

logger = logging.getLogger("audit_logger")

class AuditLogger:
    def __init__(self):
        self.db_path = os.path.join(BASE_TEMP, "contract_assistant.db")
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self):
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    status TEXT DEFAULT 'SUCCESS',
                    duration_ms REAL DEFAULT 0
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to initialize audit_logs table: {e}")

    def log_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        status: str = "SUCCESS",
        ip_address: Optional[str] = "127.0.0.1",
        user_agent: Optional[str] = "Client",
        duration_ms: float = 0
    ) -> bool:
        """
        Record a secure audit log event.
        """
        now = datetime.now().isoformat()
        details_str = json.dumps(details)

        # 1. Database persistence
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO audit_logs (timestamp, event_type, ip_address, user_agent, details, status, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (now, event_type, ip_address, user_agent, details_str, status, duration_ms))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to write audit log to DB: {e}")

        # 2. File persistence (JSONL for immutable stream)
        try:
            log_entry = {
                "timestamp": now,
                "event_type": event_type,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "status": status,
                "duration_ms": duration_ms,
                "details": details
            }
            with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log to file: {e}")

        return True

    def get_logs(self, limit: int = 100, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent logs (requires admin authorization)"""
        try:
            conn = self._get_conn()
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            if event_type and event_type != "ALL":
                cur.execute("""
                    SELECT * FROM audit_logs 
                    WHERE event_type = ? 
                    ORDER BY id DESC LIMIT ?
                """, (event_type, limit))
            else:
                cur.execute("""
                    SELECT * FROM audit_logs 
                    ORDER BY id DESC LIMIT ?
                """, (limit,))

            rows = cur.fetchall()
            logs = []
            for r in rows:
                parsed_details = {}
                try:
                    parsed_details = json.loads(r["details"]) if r["details"] else {}
                except Exception:
                    parsed_details = {"raw": r["details"]}

                logs.append({
                    "id": r["id"],
                    "timestamp": r["timestamp"],
                    "event_type": r["event_type"],
                    "ip_address": r["ip_address"],
                    "user_agent": r["user_agent"],
                    "details": parsed_details,
                    "status": r["status"],
                    "duration_ms": r["duration_ms"]
                })
            conn.close()
            return logs
        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get high-level analytics and traffic summary for admin"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM audit_logs")
            total_events = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM audit_logs WHERE status = 'ERROR'")
            total_errors = cur.fetchone()[0]

            # Traffic & Visitor Metrics
            cur.execute("SELECT COUNT(*) FROM audit_logs WHERE event_type = 'PAGE_VIEW'")
            total_page_views = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT ip_address) FROM audit_logs WHERE event_type = 'PAGE_VIEW'")
            unique_visitors = cur.fetchone()[0]

            today_prefix = datetime.now().strftime("%Y-%m-%d") + "%"
            cur.execute("SELECT COUNT(*) FROM audit_logs WHERE event_type = 'PAGE_VIEW' AND timestamp LIKE ?", (today_prefix,))
            views_today = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM audit_logs WHERE event_type != 'PAGE_VIEW'")
            api_transactions = cur.fetchone()[0]

            cur.execute("SELECT event_type, COUNT(*) FROM audit_logs GROUP BY event_type")
            by_type = dict(cur.fetchall())

            conn.close()
            return {
                "total_events": total_events,
                "total_errors": total_errors,
                "total_page_views": total_page_views,
                "unique_visitors": unique_visitors,
                "views_today": views_today,
                "api_transactions": api_transactions,
                "events_by_type": by_type
            }
        except Exception as e:
            logger.error(f"Failed to get audit stats: {e}")
            return {
                "total_events": 0,
                "total_errors": 0,
                "total_page_views": 0,
                "unique_visitors": 0,
                "views_today": 0,
                "api_transactions": 0,
                "events_by_type": {}
            }

    def clear_logs(self) -> bool:
        """Clear all audit logs (admin only)"""
        try:
            conn = self._get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM audit_logs")
            conn.commit()
            conn.close()
            if os.path.exists(AUDIT_FILE):
                open(AUDIT_FILE, "w").close()
            return True
        except Exception as e:
            logger.error(f"Failed to clear audit logs: {e}")
            return False

audit_logger = AuditLogger()

