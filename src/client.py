"""UDP client that performs an INIT exchange followed by DATA messages."""

from __future__ import annotations

import argparse
import socket
import time
from pathlib import Path

from eventlog import EventLog
from protocol import DATA, DATA_ACK, INIT, INIT_ACK, Message, ProtocolError, decode, encode, json_payload, parse_json_payload


def run_client(host: str, port: int, client_name: str, start: int, count: int, log_path: str | Path, timeout: float = 0.2, retries: int = 5) -> int:
    log = EventLog(log_path)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    server = (host, port)
    try:
        worker_id = _init(sock, server, client_name, log, retries)
        for sequence in range(start, start + count):
            message = Message(DATA, task_id=sequence, worker_id=worker_id, payload=json_payload({"worker_id": worker_id, "sequence": sequence, "value": sequence * 2}))
            _exchange(sock, server, message, DATA_ACK, log, retries)
        log.write("client", "complete", detail=f"worker_id={worker_id},count={count}")
        return worker_id
    finally:
        sock.close()
        log.close()


def _init(sock: socket.socket, server: tuple[str, int], name: str, log: EventLog, retries: int) -> int:
    response = _exchange(sock, server, Message(INIT, payload=json_payload({"client": name})), INIT_ACK, log, retries)
    worker_id = parse_json_payload(response.payload).get("worker_id")
    if not isinstance(worker_id, int) or worker_id <= 0:
        raise ProtocolError("server returned an invalid worker ID")
    log.write("client", "init_complete", peer=f"{server[0]}:{server[1]}", detail=f"worker_id={worker_id}")
    return worker_id


def _exchange(sock: socket.socket, server: tuple[str, int], message: Message, expected_type: int, log: EventLog, retries: int) -> Message:
    packet = encode(message)
    for attempt in range(1, retries + 1):
        sock.sendto(packet, server)
        log.write("client", "send", peer=f"{server[0]}:{server[1]}", task_id=message.task_id, detail=f"type={message.message_type},attempt={attempt}")
        deadline = time.monotonic() + sock.gettimeout()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                response_packet, address = sock.recvfrom(65535)
            except socket.timeout:
                break
            if address != server:
                continue
            try:
                response = decode(response_packet)
            except ProtocolError:
                continue
            if response.message_type == expected_type and response.task_id == message.task_id:
                return response
        log.write("client", "retry", peer=f"{server[0]}:{server[1]}", task_id=message.task_id, detail=f"attempt={attempt}")
    raise TimeoutError(f"no acknowledgement for task {message.task_id} after {retries} attempts")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--name", default="client")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--log", default="results/client.csv")
    args = parser.parse_args()
    worker_id = run_client(args.host, args.port, args.name, args.start, args.count, args.log)
    print(f"CLIENT_COMPLETE worker_id={worker_id} count={args.count}", flush=True)


if __name__ == "__main__":
    main()
