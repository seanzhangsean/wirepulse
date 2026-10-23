"""
Unit tests for PeerMonitor rate computation.
"""

import time
import unittest
from wirepulse.monitor import PeerMonitor
from wirepulse.parser import WireGuardParser


MOCK_DUMP_T1 = """
dummyPrivKey	ifacePubkey=	51820	off
peerKey1=	(none)	1.1.1.1:51820	10.0.0.2/32	1700000000	1000	2000	25
"""

MOCK_DUMP_T2 = """
dummyPrivKey	ifacePubkey=	51820	off
peerKey1=	(none)	1.1.1.1:51820	10.0.0.2/32	1700000000	6000	12000	25
"""


class TestMonitor(unittest.TestCase):
    def test_peer_monitor_rate_calculation(self):
        parser = WireGuardParser()
        monitor = PeerMonitor(parser=parser)

        # First poll
        stats1 = monitor.poll_interface("wg0", raw_dump=MOCK_DUMP_T1)
        self.assertEqual(stats1.total_peers, 1)
        rate1 = monitor.get_rate("wg0", "peerKey1=")
        self.assertIsNone(rate1)

        # Small sleep
        time.sleep(0.05)

        # Second poll
        stats2 = monitor.poll_interface("wg0", raw_dump=MOCK_DUMP_T2)
        self.assertEqual(stats2.total_peers, 1)
        rate2 = monitor.get_rate("wg0", "peerKey1=")
        self.assertIsNotNone(rate2)
        self.assertGreater(rate2.rx_bytes_per_sec, 0)
        self.assertGreater(rate2.tx_bytes_per_sec, 0)


if __name__ == "__main__":
    unittest.main()
