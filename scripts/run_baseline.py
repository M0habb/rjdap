"""Run the Baseline local scenario: one server and four deterministic clients."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--tasks", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--results", type=Path, default=ROOT / "results" / "baseline")
    args = parser.parse_args()
    if args.tasks < 1 or args.workers < 1 or args.tasks % args.workers:
        raise SystemExit("--tasks must be positive and divisible by --workers")
    args.results.mkdir(parents=True, exist_ok=True)
    server_log = args.results / "server.csv"
    server = subprocess.Popen(
        [sys.executable, str(SRC / "server.py"), "--port", str(args.port), "--expected-data", str(args.tasks), "--log", str(server_log)],
        cwd=SRC,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        ready = server.stdout.readline().strip() if server.stdout else ""
        if not ready.startswith("SERVER_READY"):
            raise RuntimeError(f"server did not start: {ready}")
        per_worker = args.tasks // args.workers
        for worker in range(args.workers):
            subprocess.run(
                [
                    sys.executable,
                    str(SRC / "client.py"),
                    "--port",
                    str(args.port),
                    "--name",
                    f"baseline-{worker + 1}",
                    "--start",
                    str(worker * per_worker + 1),
                    "--count",
                    str(per_worker),
                    "--log",
                    str(args.results / f"client_{worker + 1}.csv"),
                ],
                cwd=SRC,
                check=True,
                capture_output=True,
                text=True,
            )
        complete = server.communicate(timeout=10)[0]
        if "SERVER_COMPLETE" not in complete:
            raise RuntimeError(f"server did not complete: {complete}")
    finally:
        if server.poll() is None:
            server.terminate()
            server.wait(timeout=5)
    rows = list(csv.DictReader(server_log.open(newline="", encoding="utf-8")))
    received = [row for row in rows if row["event"] == "data_received" and row["detail"] == "accepted"]
    if len(received) != args.tasks:
        raise RuntimeError(f"expected {args.tasks} unique DATA records, found {len(received)}")
    expected_logs = [server_log, *[args.results / f"client_{i}.csv" for i in range(1, args.workers + 1)]]
    missing = [str(path) for path in expected_logs if not path.exists()]
    if missing:
        raise RuntimeError(f"missing logs: {', '.join(missing)}")
    print(f"BASELINE_PASS tasks={len(received)} workers={args.workers} logs={args.results}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())