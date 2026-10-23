"""
WireGuard interface and peer telemetry parser.
Parses the output of `wg show <interface> dump` into structured, strongly-typed objects.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PeerStats:
    public_key: str
    preshared_key: str
    endpoint: str
    allowed_ips: List[str]
    latest_handshake_epoch: int
    bytes_rx: int
    bytes_tx: int
    persistent_keepalive: str
    interface: str
    alias: Optional[str] = None

    @property
    def seconds_since_last_handshake(self) -> int:
        if self.latest_handshake_epoch <= 0:
            return -1
        current_epoch = int(time.time())
        diff = current_epoch - self.latest_handshake_epoch
        return max(0, diff)

    @property
    def is_active(self) -> bool:
        """
        WireGuard renegotiates handshakes every 120s if active.
        We mark a peer as active if handshake occurred within last 180s.
        """
        sec = self.seconds_since_last_handshake
        return 0 <= sec <= 180

    @property
    def short_key(self) -> str:
        if len(self.public_key) > 8:
            return f"{self.public_key[:4]}...{self.public_key[-4:]}"
        return self.public_key


@dataclass
class InterfaceStats:
    name: str
    public_key: str
    listen_port: int
    fwmark: str
    peers: List[PeerStats]

    @property
    def total_peers(self) -> int:
        return len(self.peers)

    @property
    def active_peers(self) -> int:
        return sum(1 for p in self.peers if p.is_active)

    @property
    def total_rx_bytes(self) -> int:
        return sum(p.bytes_rx for p in self.peers)

    @property
    def total_tx_bytes(self) -> int:
        return sum(p.bytes_tx for p in self.peers)


class WireGuardParser:
    """
    Executes and parses wireguard command-line output.
    Can also parse raw text buffers directly for testing and offline analysis.
    """

    def __init__(self, peer_aliases: Optional[Dict[str, str]] = None):
        self.peer_aliases = peer_aliases or {}

    def fetch_dump(self, interface: str) -> str:
        """
        Invokes `wg show <interface> dump`.
        """
        cmd = ["wg", "show", interface, "dump"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError("WireGuard CLI tool ('wg') is not installed or not in PATH.")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to query WireGuard interface '{interface}': {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out while querying interface '{interface}'.")

    def parse_dump(self, interface_name: str, raw_output: str) -> InterfaceStats:
        """
        Parse raw output of `wg show <interface> dump`.
        Format specification:
        Line 0 (Interface):
          [0] private_key (hidden or hash)
          [1] public_key
          [2] listen_port
          [3] fwmark (optional/off)
        Line 1..N (Peers):
          [0] public_key
          [1] preshared_key
          [2] endpoint
          [3] allowed_ips (comma-separated)
          [4] latest_handshake (unix epoch)
          [5] bytes_rx
          [6] bytes_tx
          [7] persistent_keepalive
        """
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        if not lines:
            return InterfaceStats(
                name=interface_name,
                public_key="",
                listen_port=0,
                fwmark="off",
                peers=[],
            )

        # Parse interface header
        iface_tokens = lines[0].split("\t")
        if len(iface_tokens) < 3:
            # Fallback to whitespace split if tab is not present
            iface_tokens = lines[0].split()

        public_key = iface_tokens[1] if len(iface_tokens) > 1 else ""
        try:
            listen_port = int(iface_tokens[2]) if len(iface_tokens) > 2 else 0
        except ValueError:
            listen_port = 0
        fwmark = iface_tokens[3] if len(iface_tokens) > 3 else "off"

        peers: List[PeerStats] = []
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 8:
                parts = line.split()

            if len(parts) < 8:
                continue

            peer_pubkey = parts[0]
            psk = parts[1]
            endpoint = parts[2]
            allowed_ips = [ip.strip() for ip in parts[3].split(",") if ip.strip()]

            try:
                latest_handshake = int(parts[4])
            except ValueError:
                latest_handshake = 0

            try:
                rx = int(parts[5])
            except ValueError:
                rx = 0

            try:
                tx = int(parts[6])
            except ValueError:
                tx = 0

            keepalive = parts[7]
            alias = self.peer_aliases.get(peer_pubkey)

            peers.append(
                PeerStats(
                    public_key=peer_pubkey,
                    preshared_key=psk,
                    endpoint=endpoint,
                    allowed_ips=allowed_ips,
                    latest_handshake_epoch=latest_handshake,
                    bytes_rx=rx,
                    bytes_tx=tx,
                    persistent_keepalive=keepalive,
                    interface=interface_name,
                    alias=alias,
                )
            )

        return InterfaceStats(
            name=interface_name,
            public_key=public_key,
            listen_port=listen_port,
            fwmark=fwmark,
            peers=peers,
        )

    def parse_interface(self, interface_name: str) -> InterfaceStats:
        raw = self.fetch_dump(interface_name)
        return self.parse_dump(interface_name, raw)
