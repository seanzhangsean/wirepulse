"""
Unit tests for WirePulse configuration parsing and environment handling.
"""

import json
import os
import tempfile
import unittest
from wirepulse.config import WirePulseConfig


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        config = WirePulseConfig()
        self.assertEqual(config.interfaces, ["wg0"])
        self.assertEqual(config.listen_address, "0.0.0.0")
        self.assertEqual(config.listen_port, 9182)
        self.assertEqual(config.poll_interval, 5)
        self.assertEqual(config.metrics_path, "/metrics")

    def test_from_dict(self):
        data = {
            "interfaces": ["wg0", "wg1"],
            "listen_port": 9999,
            "listen_address": "127.0.0.1",
            "peer_aliases": {"pubkey123=": "server-alpha"},
        }
        config = WirePulseConfig.from_dict(data)
        self.assertEqual(config.interfaces, ["wg0", "wg1"])
        self.assertEqual(config.listen_port, 9999)
        self.assertEqual(config.listen_address, "127.0.0.1")
        self.assertEqual(config.peer_aliases["pubkey123="], "server-alpha")

    def test_env_var_override(self):
        old_ifaces = os.environ.get("WIREPULSE_INTERFACES")
        old_port = os.environ.get("WIREPULSE_LISTEN_PORT")
        old_addr = os.environ.get("WIREPULSE_LISTEN_ADDR")
        try:
            os.environ["WIREPULSE_INTERFACES"] = "vpn0, vpn1"
            os.environ["WIREPULSE_LISTEN_PORT"] = "9200"
            os.environ["WIREPULSE_LISTEN_ADDR"] = "192.168.1.1"

            config = WirePulseConfig.load()
            self.assertEqual(config.interfaces, ["vpn0", "vpn1"])
            self.assertEqual(config.listen_port, 9200)
            self.assertEqual(config.listen_address, "192.168.1.1")
        finally:
            if old_ifaces is not None:
                os.environ["WIREPULSE_INTERFACES"] = old_ifaces
            else:
                os.environ.pop("WIREPULSE_INTERFACES", None)

            if old_port is not None:
                os.environ["WIREPULSE_LISTEN_PORT"] = old_port
            else:
                os.environ.pop("WIREPULSE_LISTEN_PORT", None)

            if old_addr is not None:
                os.environ["WIREPULSE_LISTEN_ADDR"] = old_addr
            else:
                os.environ.pop("WIREPULSE_LISTEN_ADDR", None)

    def test_load_from_json(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
            payload = {
                "interfaces": ["wg-mesh"],
                "listen_port": 8080,
            }
            json.dump(payload, tf)
            tf.flush()
            tmp_path = tf.name

        try:
            config = WirePulseConfig.load(tmp_path)
            self.assertEqual(config.interfaces, ["wg-mesh"])
            self.assertEqual(config.listen_port, 8080)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
