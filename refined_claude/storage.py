import os
import re
import sqlite3
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Tuple

log = logging.getLogger(__name__)

# Constants
DEFAULT_SNAPSHOT_DIR = "snapshots"
DEFAULT_DB_FILE = "snapshots.db"


class SnapshotStorage:
    """Manages snapshot storage, including database and file operations."""

    def __init__(self, base_dir: str = None):
        """Initialize the storage manager.

        Args:
            base_dir: Base directory for storing snapshots. If None, uses CWD.
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.snapshot_dir = self.base_dir / DEFAULT_SNAPSHOT_DIR
        self.db_path = self.base_dir / DEFAULT_DB_FILE

        # Ensure directories exist
        self.snapshot_dir.mkdir(exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_snapshots (
                uuid TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()
        log.info(f"Database initialized at {self.db_path}")

    def generate_slug(self, title: str) -> str:
        """Generate a slug from a chat title.

        Args:
            title: The title to generate a slug from.

        Returns:
            A URL-friendly slug.
        """
        if not title:
            return "untitled-chat"

        # Remove special characters and replace spaces with hyphens
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_-]+", "-", slug)
        slug = re.sub(r"^-+|-+$", "", slug)

        # Truncate to a reasonable length
        if len(slug) > 50:
            slug = slug[:50]

        return slug

    def extract_title_from_content(self, content: str) -> str:
        """Extract a title from the chat content.

        This attempts to find meaningful text from the first few exchanges
        to use as a title.

        Args:
            content: The full chat content.

        Returns:
            A string to use as a title.
        """
        # Look for the first user message
        user_message_match = re.search(
            r"User:\s*\n\n(.*?)(?=\n\n----\n\n|$)", content, re.DOTALL
        )
        if user_message_match:
            first_line = user_message_match.group(1).strip().split("\n")[0]
            # Take the first 5-10 words as the title
            words = first_line.split()
            if words:
                title_words = words[: min(10, len(words))]
                return " ".join(title_words)

        return "Untitled Chat"

    def get_snapshot_path(self, uuid: str, content: str) -> Tuple[str, bool]:
        """Get the path to save a snapshot for a given UUID.

        If an entry exists in the database, returns the existing path.
        Otherwise, creates a new entry and returns the new path.

        Args:
            uuid: The chat UUID.
            content: The chat content (used to generate a title if needed).

        Returns:
            A tuple of (file path, is_new_file).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if an entry exists for this UUID
        cursor.execute(
            "SELECT filename, title FROM chat_snapshots WHERE uuid = ?", (uuid,)
        )
        result = cursor.fetchone()

        if result:
            filename, title = result
            conn.close()
            return os.path.join(self.snapshot_dir, filename), False

        # Extract a title from the content
        title = self.extract_title_from_content(content)

        # Generate a date-based prefix
        date_prefix = time.strftime("%Y%m%d")

        # Generate a slug from the title
        slug = self.generate_slug(title)

        # Create a unique filename
        filename = f"{date_prefix}-{slug}.txt"

        # Ensure filename is unique
        base_name = f"{date_prefix}-{slug}"
        ext = ".txt"
        counter = 1
        while os.path.exists(os.path.join(self.snapshot_dir, filename)):
            filename = f"{base_name}-{counter}{ext}"
            counter += 1

        # Add entry to database
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO chat_snapshots (uuid, filename, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (uuid, filename, title, now, now),
        )

        conn.commit()
        conn.close()

        return os.path.join(self.snapshot_dir, filename), True

    def update_snapshot(self, uuid: str, content: str) -> str:
        """Update or create a snapshot for the given UUID.

        Args:
            uuid: The chat UUID.
            content: The chat content to save.

        Returns:
            The path to the saved file.
        """
        file_path, is_new = self.get_snapshot_path(uuid, content)

        with open(file_path, "w") as f:
            f.write(content)

        # Update the updated_at timestamp
        if not is_new:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "UPDATE chat_snapshots SET updated_at = ? WHERE uuid = ?",
                (now, uuid),
            )
            conn.commit()
            conn.close()

        log.info(f"{'Created' if is_new else 'Updated'} snapshot at {file_path}")
        return file_path

    def list_snapshots(self) -> Dict[str, Dict]:
        """List all snapshots in the database.

        Returns:
            A dictionary mapping UUIDs to snapshot info.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT uuid, filename, title, created_at, updated_at FROM chat_snapshots ORDER BY updated_at DESC"
        )

        snapshots = {}
        for row in cursor.fetchall():
            uuid, filename, title, created_at, updated_at = row
            snapshots[uuid] = {
                "filename": filename,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "path": os.path.join(self.snapshot_dir, filename),
            }

        conn.close()
        return snapshots
