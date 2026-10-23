"""
Terminal UI and tabular status renderer for WirePulse.
Supports both one-shot status inspection and continuous live TUI refresh.
"""

from __future__ import annotations

import os
import sys
import time
from typing import List
from wirepulse import __version__
from wirepulse.monitor import PeerMonitor
from wirepulse.parser import InterfaceStats, PeerStats


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable B, KiB, MiB, GiB."""
    val = float(num_bytes)
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if abs(val) < 1024.0:
            return f"{val:6.1f} {unit}"
        val /= 1024.0
    return f"{val:6.1f} PiB"


def format_handshake(seconds: int) -> str:
    """Format seconds elapsed since handshake into a readable duration."""
    if seconds < 0:
        return "Never"
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m {seconds % 60}s"
    hours = minutes // 60
    return f"{hours}h {minutes % 60}m"


class TerminalRenderer:
    @staticmethod
    def render_table(iface_stats: List[InterfaceStats], monitor: PeerMonitor) -> str:
        lines: List[str] = []
        header = f" WirePulse v{__version__} - WireGuard Telemetry Dashboard"
        lines.append("=" * 82)
        lines.append(header)
        lines.append("=" * 82)

        for iface in iface_stats:
            active_badge = f"{iface.active_peers}/{iface.total_peers} peers active"
            lines.append(
                f"Interface: {iface.name:<10} Port: {iface.listen_port:<8} Status: [{active_badge}]"
            )
            lines.append(
                f"Public Key: {iface.public_key if iface.public_key else 'N/A'}"
            )
            lines.append("-" * 82)
            lines.append(
                f"{'PEER / ALIAS':<22} {'ENDPOINT':<20} {'HANDSHAKE':<12} {'RX':<10} {'TX':<10} {'STATUS':<6}"
            )
            lines.append("-" * 82)

            if not iface.peers:
                lines.append("  (No peers configured)")
            else:
                for peer in iface.peers:
                    name_display = peer.alias or peer.short_key
                    if len(name_display) > 20:
                        name_display = name_display[:17] + "..."

                    endpoint_display = peer.endpoint if peer.endpoint != "(none)" else "-"
                    if len(endpoint_display) > 19:
                        endpoint_display = endpoint_display[:16] + "..."

                    hs_str = format_handshake(peer.seconds_since_last_handshake)
                    rx_str = format_bytes(peer.bytes_rx).strip()
                    tx_str = format_bytes(peer.bytes_tx).strip()
                    status_str = "ONLINE" if peer.is_active else "IDLE"

                    lines.append(
                        f"{name_display:<22} {endpoint_display:<20} {hs_str:<12} {rx_str:<10} {tx_str:<10} {status_str:<6}"
                    )

            lines.append("-" * 82)
            lines.append("")

        return "\n".join(lines)


def run_live_tui(interfaces: List[str], interval: int = 2) -> None:
    monitor = PeerMonitor()
    try:
        while True:
            # Clear terminal
            os.system("clear" if os.name != "nt" else "cls")
            stats_list: List[InterfaceStats] = []
            for iface in interfaces:
                try:
                    stats_list.append(monitor.poll_interface(iface))
                except Exception as e:
                    print(f"Error reading interface {iface}: {e}", file=sys.stderr)

            print(TerminalRenderer.render_table(stats_list, monitor))
            print(f"Refreshing every {interval}s. Press Ctrl+C to exit.")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nExiting WirePulse TUI.")
