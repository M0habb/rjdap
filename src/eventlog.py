"""CSV event logging shared by the UDP demo processes."""

from __future__ import annotations

import csv
import threading
from datetime import datetime, timezone
from pathlib import Path


class EventLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["timestamp", "role", "event", "peer", "task_id", "detail"])
        self._file.flush()

    def write(self, role: str, event: str, peer: str = "", task_id: int = 0, detail: str = "") -> None:
        with self._lock:
            self._writer.writerow([datetime.now(timezone.utc).isoformat(), role, event, peer, task_id, detail])
            self._file.flush()

    def close(self) -> None:
        self._file.close()