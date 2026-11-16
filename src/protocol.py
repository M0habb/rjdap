"""Wire format for the local UDP INIT/DATA prototype."""

from __future__ import annotations

import binascii
import json
import struct
from dataclasses import dataclass

HEADER_FORMAT = "!BBIHHIHHHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_PACKET_SIZE = 512
MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - HEADER_SIZE
VERSION = 1

INIT = 1
INIT_ACK = 2
DATA = 3
DATA_ACK = 4


class ProtocolError(ValueError):
    """Raised when a datagram is not a valid protocol packet."""


@dataclass(frozen=True)
class Message:
    message_type: int
    task_id: int = 0
    worker_id: int = 0
    attempt: int = 1
    payload: bytes = b""
    fragment_id: int = 0
    fragment_index: int = 0
    fragment_count: int = 1


def encode(message: Message) -> bytes:
    """Encode a message and add its CRC-32 checksum."""
    if len(message.payload) > MAX_PAYLOAD_SIZE:
        raise ProtocolError(f"payload exceeds {MAX_PAYLOAD_SIZE} bytes")
    if not 0 <= message.message_type <= 255:
        raise ProtocolError("message type must fit in one byte")
    if not 0 <= message.task_id <= 0xFFFFFFFF:
        raise ProtocolError("task_id must fit in four bytes")
    header = struct.pack(
        HEADER_FORMAT,
        VERSION,
        message.message_type,
        message.task_id,
        message.worker_id,
        message.attempt,
        0,
        len(message.payload),
        message.fragment_id,
        message.fragment_index,
        message.fragment_count,
    )
    checksum = binascii.crc32(header + message.payload) & 0xFFFFFFFF
    header = struct.pack(
        HEADER_FORMAT,
        VERSION,
        message.message_type,
        message.task_id,
        message.worker_id,
        message.attempt,
        checksum,
        len(message.payload),
        message.fragment_id,
        message.fragment_index,
        message.fragment_count,
    )
    return header + message.payload


def decode(packet: bytes) -> Message:
    """Validate and decode one UDP datagram."""
    if len(packet) < HEADER_SIZE:
        raise ProtocolError("packet is shorter than the fixed header")
    values = struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])
    version, message_type, task_id, worker_id, attempt, checksum, payload_length, fragment_id, fragment_index, fragment_count = values
    payload = packet[HEADER_SIZE:]
    if version != VERSION:
        raise ProtocolError(f"unsupported protocol version: {version}")
    if payload_length != len(payload):
        raise ProtocolError("payload length does not match packet length")
    if fragment_count == 0 or fragment_index >= fragment_count:
        raise ProtocolError("invalid fragment fields")
    zero_checksum = struct.pack(
        HEADER_FORMAT,
        version,
        message_type,
        task_id,
        worker_id,
        attempt,
        0,
        payload_length,
        fragment_id,
        fragment_index,
        fragment_count,
    )
    expected = binascii.crc32(zero_checksum + payload) & 0xFFFFFFFF
    if checksum != expected:
        raise ProtocolError("CRC-32 checksum mismatch")
    return Message(
        message_type,
        task_id,
        worker_id,
        attempt,
        payload,
        fragment_id,
        fragment_index,
        fragment_count,
    )


def json_payload(value: dict[str, object]) -> bytes:
    """Serialize a small control payload deterministically."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def parse_json_payload(payload: bytes) -> dict[str, object]:
    """Parse a JSON control payload and reject non-object values."""
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ProtocolError("JSON payload must be an object")
    return value