"""
CLI entry point for WirePulse.
Supports:
  - wirepulse serve: Starts background Prometheus exporter HTTP daemon.
  - wirepulse status: Displays one-shot peer and interface health table.
  - wirepulse top: Interactive terminal dashboard with live refresh.
  - wirepulse check: Validates wg tool availability and configured interfaces.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from wirepulse import __version__
from wirepulse.config import WirePulseConfig
from wirepulse.exporter import PrometheusExporter
from wirepulse.monitor import PeerMonitor
from wirepulse.parser import WireGuardParser
from wirepulse.tui import TerminalRenderer, run_live_tui


def configure_logging(level_name: str) -> None:
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_serve(args: argparse.Namespace) -> int:
    config = WirePulseConfig.load(args.config)
    if args.port:
        config.listen_port = args.port
    if args.host:
        config.listen_address = args.host
    if args.interfaces:
        config.interfaces = [i.strip() for i in args.interfaces.split(",") if i.strip()]

    configure_logging(config.log_level)
    parser = WireGuardParser(peer_aliases=config.peer_aliases)
    monitor = PeerMonitor(parser=parser)
    exporter = PrometheusExporter(config, monitor=monitor)
    exporter.start()
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    config = WirePulseConfig.load(args.config)
    interfaces = (
        [i.strip() for i in args.interfaces.split(",") if i.strip()]
        if args.interfaces
        else config.interfaces
    )

    parser = WireGuardParser(peer_aliases=config.peer_aliases)
    monitor = PeerMonitor(parser=parser)

    stats_list = []
    for iface in interfaces:
        try:
            stats = monitor.poll_interface(iface)
            stats_list.append(stats)
        except Exception as e:
            print(f"Error checking interface '{iface}': {e}", file=sys.stderr)

    if args.json:
        # Export structured JSON
        json_data = []
        for iface in stats_list:
            json_data.append({
                "interface": iface.name,
                "public_key": iface.public_key,
                "listen_port": iface.listen_port,
                "total_peers": iface.total_peers,
                "active_peers": iface.active_peers,
                "total_rx_bytes": iface.total_rx_bytes,
                "total_tx_bytes": iface.total_tx_bytes,
                "peers": [
                    {
                        "public_key": p.public_key,
                        "alias": p.alias,
                        "endpoint": p.endpoint,
                        "allowed_ips": p.allowed_ips,
                        "latest_handshake_epoch": p.latest_handshake_epoch,
                        "seconds_since_handshake": p.seconds_since_last_handshake,
                        "bytes_rx": p.bytes_rx,
                        "bytes_tx": p.bytes_tx,
                        "is_active": p.is_active,
                    }
                    for p in iface.peers
                ],
            })
        print(json.dumps(json_data, indent=2))
    else:
        print(TerminalRenderer.render_table(stats_list, monitor))

    return 0


def cmd_top(args: argparse.Namespace) -> int:
    config = WirePulseConfig.load(args.config)
    interfaces = (
        [i.strip() for i in args.interfaces.split(",") if i.strip()]
        if args.interfaces
        else config.interfaces
    )
    run_live_tui(interfaces, interval=args.interval)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    print(f"WirePulse v{__version__} - Environment Diagnostic")
    print("-" * 50)
    config = WirePulseConfig.load(args.config)
    parser = WireGuardParser()

    # Check wg binary
    import shutil
    wg_path = shutil.which("wg")
    if wg_path:
        print(f"[OK] WireGuard utility found at: {wg_path}")
    else:
        print("[WARN] 'wg' executable not found in PATH.")

    # Check interfaces
    for iface in config.interfaces:
        try:
            stats = parser.parse_interface(iface)
            print(f"[OK] Interface '{iface}' active: {stats.total_peers} peers, port {stats.listen_port}")
        except Exception as e:
            print(f"[FAIL] Interface '{iface}' not accessible: {e}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wirepulse",
        description="Lightweight WireGuard telemetry daemon and Prometheus exporter.",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"wirepulse {__version__}"
    )
    parser.add_argument(
        "-c", "--config", help="Path to wirepulse.json configuration file"
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Serve
    serve_parser = subparsers.add_parser("serve", help="Run Prometheus exporter HTTP daemon")
    serve_parser.add_argument("-p", "--port", type=int, help="HTTP listen port (default: 9182)")
    serve_parser.add_argument("-H", "--host", type=str, help="HTTP listen host (default: 0.0.0.0)")
    serve_parser.add_argument(
        "-i", "--interfaces", type=str, help="Comma-separated interface list (e.g. wg0,wg1)"
    )

    # Status
    status_parser = subparsers.add_parser("status", help="Print one-shot status report")
    status_parser.add_argument("-i", "--interfaces", type=str, help="Interfaces to inspect")
    status_parser.add_argument("--json", action="store_true", help="Output in JSON format")

    # Top
    top_parser = subparsers.add_parser("top", help="Live interactive terminal dashboard")
    top_parser.add_argument("-i", "--interfaces", type=str, help="Interfaces to monitor")
    top_parser.add_argument(
        "-n", "--interval", type=int, default=2, help="Refresh interval in seconds"
    )

    # Check
    subparsers.add_parser("check", help="Diagnostic check of system & interfaces")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "serve": cmd_serve,
        "status": cmd_status,
        "top": cmd_top,
        "check": cmd_check,
    }

    exit_code = dispatch[args.subcommand](args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
