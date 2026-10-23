"""
Unit tests for WireGuard dump parser.
"""

import time
import unittest
from wirepulse.parser import WireGuardParser, InterfaceStats, PeerStats


MOCK_WG_DUMP = """
iK35...privateKey	pubKeyIface1234567890abcdef=	51820	off
peerPubKeyAAA111111111111111111111=	(none)	198.51.100.1:51820	10.0.0.2/32	1700000000	1048576	2097152	25
peerPubKeyBBB222222222222222222222=	(none)	203.0.113.5:51820	10.0.0.3/32	0	0	0	off
"""


class TestParser(unittest.TestCase):
    def test_parse_empty_dump(self):
        parser = WireGuardParser()
        stats = parser.parse_dump("wg0", "")
        self.assertEqual(stats.name, "wg0")
        self.assertEqual(stats.total_peers, 0)
        self.assertEqual(stats.peers, [])

    def test_parse_valid_dump(self):
        aliases = {
            "peerPubKeyAAA111111111111111111111=": "roadwarrior-laptop",
        }
        parser = WireGuardParser(peer_aliases=aliases)
        stats = parser.parse_dump("wg0", MOCK_WG_DUMP)

        self.assertEqual(stats.name, "wg0")
        self.assertEqual(stats.public_key, "pubKeyIface1234567890abcdef=")
        self.assertEqual(stats.listen_port, 51820)
        self.assertEqual(stats.fwmark, "off")
        self.assertEqual(stats.total_peers, 2)

        # Peer 1
        p1 = stats.peers[0]
        self.assertEqual(p1.public_key, "peerPubKeyAAA111111111111111111111=")
        self.assertEqual(p1.alias, "roadwarrior-laptop")
        self.assertEqual(p1.endpoint, "198.51.100.1:51820")
        self.assertEqual(p1.allowed_ips, ["10.0.0.2/32"])
        self.assertEqual(p1.latest_handshake_epoch, 1700000000)
        self.assertEqual(p1.bytes_rx, 1048576)
        self.assertEqual(p1.bytes_tx, 2097152)
        self.assertEqual(p1.persistent_keepalive, "25")

        # Peer 2
        p2 = stats.peers[1]
        self.assertEqual(p2.public_key, "peerPubKeyBBB222222222222222222222=")
        self.assertIsNone(p2.alias)
        self.assertEqual(p2.latest_handshake_epoch, 0)
        self.assertFalse(p2.is_active)
        self.assertEqual(p2.seconds_since_last_handshake, -1)

    def test_active_peer_calculation(self):
        current_time = int(time.time())
        recent_handshake = current_time - 45  # 45 seconds ago

        raw = f"""
dummyPrivKey	ifacePubkey=	51820	off
activePeerPubKey123456789012345678=	(none)	1.2.3.4:51820	10.0.0.5/32	{recent_handshake}	100	200	25
"""
        parser = WireGuardParser()
        stats = parser.parse_dump("wg0", raw)

        self.assertEqual(stats.active_peers, 1)
        p = stats.peers[0]
        self.assertTrue(p.is_active)
        self.assertGreaterEqual(p.seconds_since_last_handshake, 44)


if __name__ == "__main__":
    unittest.main()
