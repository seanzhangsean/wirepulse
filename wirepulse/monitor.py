"""
Stateful peer monitor and rate calculation engine.
Tracks byte deltas across polling ticks to compute instantaneous throughput.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from wirepulse.parser import InterfaceStats, PeerStats, WireGuardParser


@dataclass
class PeerRate:
    public_key: str
    rx_bytes_per_sec: float
    tx_bytes_per_sec: float
    timestamp: float


class PeerMonitor:
    def __init__(self, parser: Optional[WireGuardParser] = None):
        self.parser = parser or WireGuardParser()
        # Historical state: (interface, pubkey) -> (timestamp, rx, tx)
        self._history: Dict[tuple[str, str], tuple[float, int, int]] = {}
        self._rates: Dict[tuple[str, str], PeerRate] = {}

    def poll_interface(self, interface: str, raw_dump: Optional[str] = None) -> InterfaceStats:
        """
        Poll interface (either via shell or mock dump), update historical rates.
        """
        if raw_dump is not None:
            stats = self.parser.parse_dump(interface, raw_dump)
        else:
            stats = self.parser.parse_interface(interface)

        now = time.time()
        for peer in stats.peers:
            key = (interface, peer.public_key)
            if key in self._history:
                last_time, last_rx, last_tx = self._history[key]
                time_delta = max(0.001, now - last_time)
                rx_delta = max(0, peer.bytes_rx - last_rx)
                tx_delta = max(0, peer.bytes_tx - last_tx)

                self._rates[key] = PeerRate(
                    public_key=peer.public_key,
                    rx_bytes_per_sec=rx_delta / time_delta,
                    tx_bytes_per_sec=tx_delta / time_delta,
                    timestamp=now,
                )

            self._history[key] = (now, peer.bytes_rx, peer.bytes_tx)

        return stats

    def get_rate(self, interface: str, public_key: str) -> Optional[PeerRate]:
        return self._rates.get((interface, public_key))
