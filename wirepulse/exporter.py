"""
Lightweight Prometheus / OpenMetrics HTTP exporter.
Runs with Python's standard library `http.server`, requiring 0 third-party packages.
Ideal for constrained environments like OpenWrt / Alpine Linux.
"""

from __future__ import annotations

import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Callable, List, Optional
from wirepulse import __version__
from wirepulse.config import WirePulseConfig
from wirepulse.monitor import PeerMonitor
from wirepulse.parser import InterfaceStats


logger = logging.getLogger("wirepulse.exporter")


class PrometheusFormatter:
    """
    Renders structured WireGuard stats into Prometheus exposition text.
    """

    @staticmethod
    def format_metrics(
        interfaces: List[InterfaceStats],
        monitor: PeerMonitor,
    ) -> str:
        lines: List[str] = [
            "# HELP wireguard_build_info Static runtime build metadata",
            "# TYPE wireguard_build_info gauge",
            f'wireguard_build_info{{version="{__version__}"}} 1',
            "",
            "# HELP wireguard_interface_peers_total Total registered peers on interface",
            "# TYPE wireguard_interface_peers_total gauge",
        ]

        for iface in interfaces:
            lines.append(
                f'wireguard_interface_peers_total{{interface="{iface.name}"}} {iface.total_peers}'
            )

        lines.extend([
            "",
            "# HELP wireguard_interface_active_peers Total peers with recent handshake (<180s)",
            "# TYPE wireguard_interface_active_peers gauge",
        ])
        for iface in interfaces:
            lines.append(
                f'wireguard_interface_active_peers{{interface="{iface.name}"}} {iface.active_peers}'
            )

        lines.extend([
            "",
            "# HELP wireguard_peer_received_bytes_total Cumulative bytes received from peer",
            "# TYPE wireguard_peer_received_bytes_total counter",
        ])
        for iface in interfaces:
            for peer in iface.peers:
                alias_label = f',alias="{peer.alias}"' if peer.alias else ""
                lines.append(
                    f'wireguard_peer_received_bytes_total{{interface="{iface.name}",public_key="{peer.public_key}",endpoint="{peer.endpoint}"{alias_label}}} {peer.bytes_rx}'
                )

        lines.extend([
            "",
            "# HELP wireguard_peer_transmitted_bytes_total Cumulative bytes sent to peer",
            "# TYPE wireguard_peer_transmitted_bytes_total counter",
        ])
        for iface in interfaces:
            for peer in iface.peers:
                alias_label = f',alias="{peer.alias}"' if peer.alias else ""
                lines.append(
                    f'wireguard_peer_transmitted_bytes_total{{interface="{iface.name}",public_key="{peer.public_key}",endpoint="{peer.endpoint}"{alias_label}}} {peer.bytes_tx}'
                )

        lines.extend([
            "",
            "# HELP wireguard_peer_last_handshake_seconds Seconds elapsed since last completed handshake",
            "# TYPE wireguard_peer_last_handshake_seconds gauge",
        ])
        for iface in interfaces:
            for peer in iface.peers:
                alias_label = f',alias="{peer.alias}"' if peer.alias else ""
                sec = peer.seconds_since_last_handshake
                val = sec if sec >= 0 else 0
                lines.append(
                    f'wireguard_peer_last_handshake_seconds{{interface="{iface.name}",public_key="{peer.public_key}"{alias_label}}} {val}'
                )

        lines.extend([
            "",
            "# HELP wireguard_peer_active Current active connection flag (1 if active, 0 otherwise)",
            "# TYPE wireguard_peer_active gauge",
        ])
        for iface in interfaces:
            for peer in iface.peers:
                alias_label = f',alias="{peer.alias}"' if peer.alias else ""
                status = 1 if peer.is_active else 0
                lines.append(
                    f'wireguard_peer_active{{interface="{iface.name}",public_key="{peer.public_key}"{alias_label}}} {status}'
                )

        lines.extend([
            "",
            "# HELP wireguard_peer_rx_bytes_per_second Instantaneous inbound transfer rate",
            "# TYPE wireguard_peer_rx_bytes_per_second gauge",
        ])
        for iface in interfaces:
            for peer in iface.peers:
                alias_label = f',alias="{peer.alias}"' if peer.alias else ""
                rate = monitor.get_rate(iface.name, peer.public_key)
                rx_bps = f"{rate.rx_bytes_per_sec:.2f}" if rate else "0.00"
                lines.append(
                    f'wireguard_peer_rx_bytes_per_second{{interface="{iface.name}",public_key="{peer.public_key}"{alias_label}}} {rx_bps}'
                )

        lines.extend([
            "",
            "# HELP wireguard_peer_tx_bytes_per_second Instantaneous outbound transfer rate",
            "# TYPE wireguard_peer_tx_bytes_per_second gauge",
        ])
        for iface in interfaces:
            for peer in iface.peers:
                alias_label = f',alias="{peer.alias}"' if peer.alias else ""
                rate = monitor.get_rate(iface.name, peer.public_key)
                tx_bps = f"{rate.tx_bytes_per_sec:.2f}" if rate else "0.00"
                lines.append(
                    f'wireguard_peer_tx_bytes_per_second{{interface="{iface.name}",public_key="{peer.public_key}"{alias_label}}} {tx_bps}'
                )

        lines.append("")
        return "\n".join(lines)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def make_request_handler(
    config: WirePulseConfig,
    monitor: PeerMonitor,
) -> type[BaseHTTPRequestHandler]:

    class MetricsHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            # Suppress normal access logs to stay quiet in production
            if config.log_level == "DEBUG":
                super().log_message(format, *args)

        def do_GET(self) -> None:
            if self.path in (config.metrics_path, "/"):
                if self.path == "/":
                    # Simple redirect or landing page
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = (
                        f"<html><head><title>WirePulse v{__version__}</title></head>"
                        f"<body><h1>WirePulse Exporter</h1>"
                        f'<p><a href="{config.metrics_path}">Metrics</a></p></body></html>'
                    )
                    self.wfile.write(html.encode("utf-8"))
                    return

                # Collect from interfaces
                iface_stats: List[InterfaceStats] = []
                for iface in config.interfaces:
                    try:
                        stats = monitor.poll_interface(iface)
                        iface_stats.append(stats)
                    except Exception as e:
                        logger.error("Scrape error on %s: %s", iface, e)

                metrics_payload = PrometheusFormatter.format_metrics(
                    iface_stats,
                    monitor,
                )

                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                self.end_headers()
                self.wfile.write(metrics_payload.encode("utf-8"))
            elif self.path == "/healthz":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK\n")
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found\n")

    return MetricsHandler


class PrometheusExporter:
    def __init__(self, config: WirePulseConfig, monitor: Optional[PeerMonitor] = None):
        self.config = config
        self.monitor = monitor or PeerMonitor()
        self.server: Optional[HTTPServer] = None

    def start(self) -> None:
        handler = make_request_handler(self.config, self.monitor)
        self.server = ThreadedHTTPServer(
            (self.config.listen_address, self.config.listen_port),
            handler,
        )
        logger.info(
            "Serving WirePulse Prometheus metrics on http://%s:%d%s",
            self.config.listen_address,
            self.config.listen_port,
            self.config.metrics_path,
        )
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down WirePulse exporter...")
        finally:
            self.server.server_close()
