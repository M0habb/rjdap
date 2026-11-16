"""Run one small INIT/DATA exchange for a quick local demonstration."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def main() -> None:
    port = 9000
    log_dir = ROOT / "results"
    log_dir.mkdir(exist_ok=True)
    server = subprocess.Popen(
        [sys.executable, str(SRC / "server.py"), "--port", str(port), "--expected-data", "1", "--log", str(log_dir / "demo_server.csv")],
        cwd=SRC,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        ready = server.stdout.readline().strip() if server.stdout else ""
        if not ready.startswith("SERVER_READY"):
            raise RuntimeError(f"server did not start: {ready}")
        subprocess.run(
            [sys.executable, str(SRC / "client.py"), "--port", str(port), "--name", "demo", "--count", "1", "--log", str(log_dir / "demo_client.csv")],
            cwd=SRC,
            check=True,
        )
        server.wait(timeout=5)
        print("INIT/DATA demo completed")
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    main()