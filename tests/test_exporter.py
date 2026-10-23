"""
Unit tests for Prometheus exposition formatter.
"""

import unittest
from wirepulse.exporter import PrometheusFormatter
from wirepulse.monitor import PeerMonitor
from wirepulse.parser import InterfaceStats, PeerStats


class TestExporter(unittest.TestCase):
    def test_prometheus_formatter_output(self):
        peer = PeerStats(
            public_key="testPeerPubkey1234567890=",
            preshared_key="(none)",
            endpoint="192.0.2.1:51820",
            allowed_ips=["10.0.0.2/32"],
            latest_handshake_epoch=1700000000,
            bytes_rx=1024,
            bytes_tx=2048,
            persistent_keepalive="25",
            interface="wg0",
            alias="test-client",
        )
        iface = InterfaceStats(
            name="wg0",
            public_key="testIfacePubkey=",
            listen_port=51820,
            fwmark="off",
            peers=[peer],
        )

        monitor = PeerMonitor()
        metrics = PrometheusFormatter.format_metrics([iface], monitor)

        self.assertIn("wireguard_build_info", metrics)
        self.assertIn('wireguard_interface_peers_total{interface="wg0"} 1', metrics)
        self.assertIn(
            'wireguard_peer_received_bytes_total{interface="wg0",public_key="testPeerPubkey1234567890=",endpoint="192.0.2.1:51820",alias="test-client"} 1024',
            metrics,
        )
        self.assertIn(
            'wireguard_peer_transmitted_bytes_total{interface="wg0",public_key="testPeerPubkey1234567890=",endpoint="192.0.2.1:51820",alias="test-client"} 2048',
            metrics,
        )


if __name__ == "__main__":
    unittest.main()
