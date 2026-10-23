"""
Configuration loader and schema validator for WirePulse.
Supports environment variables, JSON config files, and fallback defaults.
Zero external dependencies for maximum compatibility with embedded Linux and OpenWrt.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_CONFIG_PATHS = [
    Path("/etc/wirepulse/wirepulse.json"),
    Path("/etc/wirepulse.json"),
    Path.home() / ".config" / "wirepulse" / "config.json",
    Path("./wirepulse.json"),
]


@dataclass
class WirePulseConfig:
    interfaces: List[str] = field(default_factory=lambda: ["wg0"])
    listen_address: str = "0.0.0.0"
    listen_port: int = 9182
    poll_interval: int = 5
    handshake_timeout_sec: int = 180
    metrics_path: str = "/metrics"
    peer_aliases: Dict[str, str] = field(default_factory=dict)
    enable_ping_probes: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, data: dict) -> WirePulseConfig:
        return cls(
            interfaces=data.get("interfaces", ["wg0"]),
            listen_address=data.get("listen_address", "0.0.0.0"),
            listen_port=int(data.get("listen_port", 9182)),
            poll_interval=int(data.get("poll_interval", 5)),
            handshake_timeout_sec=int(data.get("handshake_timeout_sec", 180)),
            metrics_path=data.get("metrics_path", "/metrics"),
            peer_aliases=data.get("peer_aliases", {}),
            enable_ping_probes=bool(data.get("enable_ping_probes", False)),
            log_level=data.get("log_level", "INFO").upper(),
        )

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> WirePulseConfig:
        """
        Load configuration from specified file or search well-known paths.
        Environment variables take ultimate precedence.
        """
        config_data: dict = {}

        candidate_paths: List[Path] = []
        if config_path:
            candidate_paths.append(Path(config_path))
        else:
            candidate_paths.extend(DEFAULT_CONFIG_PATHS)

        for path in candidate_paths:
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                    break
                except (json.JSONDecodeError, OSError) as e:
                    # Fallback gracefully
                    print(f"[Warning] Failed to parse {path}: {e}")

        # Environment variable overrides
        if "WIREPULSE_INTERFACES" in os.environ:
            config_data["interfaces"] = [
                i.strip() for i in os.environ["WIREPULSE_INTERFACES"].split(",") if i.strip()
            ]
        if "WIREPULSE_LISTEN_PORT" in os.environ:
            config_data["listen_port"] = int(os.environ["WIREPULSE_LISTEN_PORT"])
        if "WIREPULSE_LISTEN_ADDR" in os.environ:
            config_data["listen_address"] = os.environ["WIREPULSE_LISTEN_ADDR"]
        if "WIREPULSE_POLL_INTERVAL" in os.environ:
            config_data["poll_interval"] = int(os.environ["WIREPULSE_POLL_INTERVAL"])

        return cls.from_dict(config_data)
