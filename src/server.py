"""UDP server for INIT and DATA exchanges."""

from __future__ import annotations

import argparse
import socket
from pathlib import Path

from eventlog import EventLog
from protocol import DATA, DATA_ACK, INIT, INIT_ACK, Message, ProtocolError, decode, encode, json_payload, parse_json_payload


class UDPServer:
    def __init__(self, host: str, port: int, log_path: str | Path, expected_data: int = 0) -> None:
        self.host = host
        self.port = port
        self.expected_data = expected_data
        self.log = EventLog(log_path)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.port = self.socket.getsockname()[1]
        self.workers: dict[tuple[str, int], int] = {}
        self.next_worker_id = 1
        self.data_ids: set[tuple[int, int]] = set()

    def serve(self) -> int:
        self.log.write("server", "listening", detail=f"{self.host}:{self.port}")
        try:
            while self.expected_data == 0 or len(self.data_ids) < self.expected_data:
                packet, address = self.socket.recvfrom(65535)
                try:
                    message = decode(packet)
                    self._handle(message, address)
                except ProtocolError as error:
                    self.log.write("server", "drop", peer=self._peer(address), detail=str(error))
        finally:
            self.log.write("server", "complete", detail=f"unique_data={len(self.data_ids)}")
            self.log.close()
            self.socket.close()
        return len(self.data_ids)

    def _handle(self, message: Message, address: tuple[str, int]) -> None:
        peer = self._peer(address)
        if message.message_type == INIT:
            worker_id = self.workers.get(address)
            if worker_id is None:
                worker_id = self.next_worker_id
                self.next_worker_id += 1
                self.workers[address] = worker_id
                self.log.write("server", "init_received", peer=peer, detail=f"worker_id={worker_id}")
            response = Message(INIT_ACK, worker_id=worker_id, payload=json_payload({"worker_id": worker_id}))
            self.socket.sendto(encode(response), address)
            self.log.write("server", "init_ack_sent", peer=peer, detail=f"worker_id={worker_id}")
            return
        if message.message_type != DATA:
            raise ProtocolError("unexpected message type")
        worker_id = self.workers.get(address)
        if worker_id is None or message.worker_id != worker_id:
            raise ProtocolError("DATA received from an unregistered worker")
        values = parse_json_payload(message.payload)
        if values.get("worker_id") != worker_id or values.get("sequence") != message.task_id:
            raise ProtocolError("DATA identity does not match its header")
        key = (worker_id, message.task_id)
        duplicate = key in self.data_ids
        self.data_ids.add(key)
        self.log.write("server", "data_received", peer=peer, task_id=message.task_id, detail="duplicate" if duplicate else "accepted")
        response = Message(DATA_ACK, task_id=message.task_id, worker_id=worker_id, payload=json_payload({"accepted": not duplicate, "sequence": message.task_id}))
        self.socket.sendto(encode(response), address)

    @staticmethod
    def _peer(address: tuple[str, int]) -> str:
        return f"{address[0]}:{address[1]}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--log", default="results/server.csv")
    parser.add_argument("--expected-data", type=int, default=0)
    args = parser.parse_args()
    server = UDPServer(args.host, args.port, args.log, args.expected_data)
    print(f"SERVER_READY {server.port}", flush=True)
    completed = server.serve()
    print(f"SERVER_COMPLETE {completed}", flush=True)


if __name__ == "__main__":
    main()