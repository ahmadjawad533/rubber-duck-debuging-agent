"""DynamoDB integration for sessions, streaks, and global aggregate stats.

Includes TTL attribute on sessions (7-day retention) and atomic counters
for the /stats dashboard without requiring full table scans.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

SESSIONS_TABLE = os.environ.get("SESSIONS_TABLE", "RubberDuckSessions")
STATS_TABLE = os.environ.get("STATS_TABLE", "RubberDuckStats")
TTL_DAYS = 7
MAX_HISTORY_ITEMS = 20
RATE_LIMIT_SECONDS = 1.0  # Min seconds between messages per session


class Database:
    """DynamoDB Session and Stats Database Manager."""

    def __init__(self, dynamodb_resource: Optional[Any] = None):
        self._memory_sessions: Dict[str, Dict[str, Any]] = {}
        self._memory_stats: Dict[str, int] = {
            "total_sessions": 0,
            "bugs_solved": 0,
            "solved_without_show_me": 0,
            "total_questions_solved": 0,
            "total_ratings": 0,
            "positive_ratings": 0,
        }
        try:
            self.dynamodb = dynamodb_resource or boto3.resource(
                "dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1")
            )
            self.sessions_table = self.dynamodb.Table(SESSIONS_TABLE)
            self.stats_table = self.dynamodb.Table(STATS_TABLE)
            self._has_ddb = True
        except Exception as e:
            logger.warning("DynamoDB not configured, using in-memory store: %s", e)
            self._has_ddb = False

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session record by session_id."""
        if not self._has_ddb:
            return self._memory_sessions.get(session_id)
        try:
            resp = self.sessions_table.get_item(Key={"session_id": session_id})
            return resp.get("Item")
        except Exception as e:
            logger.warning("Failed to fetch session %s from DynamoDB, using fallback: %s", session_id, e)
            return self._memory_sessions.get(session_id)


    def save_session(
        self,
        session_id: str,
        history: List[Dict[str, Any]],
        question_count: int,
        hints_used: int,
        state: str,
        solved: bool,
        show_me_used: bool,
        streak: int,
        rating: Optional[str] = None,
        created_at: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Save or update session item with TTL."""
        now = int(time.time())
        created = created_at or now
        ttl = created + (TTL_DAYS * 86400)

        # Cap history to avoid prompt overflow & storage explosion
        capped_history = history[-MAX_HISTORY_ITEMS:]

        item = {
            "session_id": session_id,
            "history": capped_history,
            "question_count": question_count,
            "hints_used": hints_used,
            "state": state,
            "solved": solved,
            "show_me_used": show_me_used,
            "streak": streak,
            "rating": rating,
            "created_at": created,
            "updated_at": now,
            "ttl": ttl,
        }

        self._memory_sessions[session_id] = item

        if self._has_ddb:
            try:
                self.sessions_table.put_item(Item=item)
            except Exception as e:
                logger.warning("Failed to save session %s to DynamoDB: %s", session_id, e)

        return item

    def check_rate_limit(self, session: Optional[Dict[str, Any]]) -> bool:
        """Return True if request is allowed, False if rate-limited."""
        if not session:
            return True
        last_updated = session.get("updated_at", 0)
        now = int(time.time())
        if (now - last_updated) < RATE_LIMIT_SECONDS:
            return False
        return True

    def increment_global_stat(self, metric: str, amount: int = 1) -> None:
        """Atomically increment a global metric in the stats table."""
        self._memory_stats[metric] = self._memory_stats.get(metric, 0) + amount
        if self._has_ddb:
            try:
                self.stats_table.update_item(
                    Key={"stat_id": "global"},
                    UpdateExpression=f"ADD #m :val",
                    ExpressionAttributeNames={"#m": metric},
                    ExpressionAttributeValues={":val": amount},
                )
            except Exception as e:
                logger.warning("Failed to increment stat %s in DynamoDB: %s", metric, e)

    def record_new_session_stat(self) -> None:
        """Record a newly initiated session in global stats."""
        self.increment_global_stat("total_sessions", 1)

    def record_solved_stat(self, show_me_used: bool, question_count: int) -> None:
        """Record solved bug metrics in global stats."""
        self.increment_global_stat("bugs_solved", 1)
        self.increment_global_stat("total_questions_solved", question_count)
        if not show_me_used:
            self.increment_global_stat("solved_without_show_me", 1)

    def record_rating_stat(self, session_id: str, rating: str) -> bool:
        """Save user thumbs up/down rating on a session and update stats."""
        if session_id in self._memory_sessions:
            self._memory_sessions[session_id]["rating"] = rating
            self._memory_sessions[session_id]["updated_at"] = int(time.time())

        self.increment_global_stat("total_ratings", 1)
        if rating == "up":
            self.increment_global_stat("positive_ratings", 1)

        if self._has_ddb:
            try:
                self.sessions_table.update_item(
                    Key={"session_id": session_id},
                    UpdateExpression="SET #r = :val, updated_at = :now",
                    ExpressionAttributeNames={"#r": "rating"},
                    ExpressionAttributeValues={":val": rating, ":now": int(time.time())},
                )
            except Exception as e:
                logger.warning("Failed to record rating in DynamoDB for session %s: %s", session_id, e)

        return True

    def get_stats(self) -> Dict[str, Any]:
        """Fetch live stats aggregated for the Results / Stats page."""
        item = dict(self._memory_stats)
        if self._has_ddb:
            try:
                resp = self.stats_table.get_item(Key={"stat_id": "global"})
                ddb_item = resp.get("Item")
                if ddb_item:
                    item = ddb_item
            except Exception as e:
                logger.warning("Failed to fetch global stats from DynamoDB: %s", e)


        total_sessions = int(item.get("total_sessions", 0))
        bugs_solved = int(item.get("bugs_solved", 0))
        solved_without_show_me = int(item.get("solved_without_show_me", 0))
        total_questions_solved = int(item.get("total_questions_solved", 0))
        total_ratings = int(item.get("total_ratings", 0))
        positive_ratings = int(item.get("positive_ratings", 0))

        solved_without_show_me_pct = (
            round((solved_without_show_me / bugs_solved) * 100, 1)
            if bugs_solved > 0
            else 100.0
        )
        avg_questions = (
            round(total_questions_solved / bugs_solved, 1)
            if bugs_solved > 0
            else 0.0
        )
        thumbs_up_pct = (
            round((positive_ratings / total_ratings) * 100, 1)
            if total_ratings > 0
            else 100.0
        )

        return {
            "total_sessions": total_sessions,
            "bugs_solved": bugs_solved,
            "solved_without_show_me": solved_without_show_me,
            "solved_without_show_me_pct": solved_without_show_me_pct,
            "avg_questions": avg_questions,
            "total_ratings": total_ratings,
            "positive_ratings": positive_ratings,
            "thumbs_up_pct": thumbs_up_pct,
        }
