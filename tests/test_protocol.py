import unittest

from src.protocol import DATA, Message, ProtocolError, decode, encode


class ProtocolTests(unittest.TestCase):
    def test_round_trip_preserves_message(self):
        message = Message(DATA, task_id=42, worker_id=7, attempt=2, payload=b"hello")
        self.assertEqual(decode(encode(message)), message)

    def test_corrupt_packet_is_rejected(self):
        packet = bytearray(encode(Message(DATA, task_id=42, payload=b"hello")))
        packet[-1] ^= 1
        with self.assertRaisesRegex(ProtocolError, "CRC"):
            decode(bytes(packet))

    def test_payload_length_is_checked(self):
        packet = encode(Message(DATA, payload=b"hello"))[:-1]
        with self.assertRaisesRegex(ProtocolError, "payload length"):
            decode(packet)


if __name__ == "__main__":
    unittest.main()