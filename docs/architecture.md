# WirePulse Architecture & Technical Design

## Overview

WirePulse is an ultra-lightweight telemetry daemon and Prometheus exporter purpose-built for WireGuard deployments on constrained edge devices, embedded gateways, and OpenWrt routers.

Traditional monitoring exporters written in Go or Node.js often consume 30MB–80MB of resident RAM and require complex runtime dependencies. In contrast, WirePulse utilizes standard library constructs in Python with zero third-party dependencies, maintaining a resident memory footprint typically under **12MB RAM** while executing non-blocking, multi-threaded metrics scrapes.

---

## Architectural Diagram

```
 +------------------------------------------------------------+
 |                      Linux / OpenWrt Kernel                |
 |                                                            |
 |  [ wg0 / wireguard kernel module ]                         |
 +-----------------------------+------------------------------+
                               |
                               | (wg show <iface> dump)
                               v
 +------------------------------------------------------------+
 |                        WirePulse                           |
 |                                                            |
 |   +--------------------+       +-----------------------+   |
 |   |  WireGuardParser   | ----> |      PeerMonitor      |   |
 |   |  (Tokenizes Dump)  |       |  (Rates, Deltas, Stat)|   |
 |   +--------------------+       +-----------+-----------+   |
 |                                            |               |
 |         +----------------------------------+               |
 |         |                                  |               |
 |         v                                  v               |
 |  +---------------+                 +---------------+       |
 |  |  Terminal TUI |                 |  Prometheus   |       |
 |  |  (Live View)  |                 |  Exporter     |       |
 |  +---------------+                 |  (:9182/http) |       |
 |                                    +-------+-------+       |
 +--------------------------------------------|---------------+
                                              | Scrape (:9182/metrics)
                                              v
                                   [ Prometheus / Grafana ]
```

---

## Component Breakdown

### 1. `WireGuardParser` (`wirepulse/parser.py`)
- Executes `wg show <interface> dump` directly or ingests raw buffers.
- Tokenizes tab-delimited dump lines into `InterfaceStats` and `PeerStats` dataclasses.
- Resolves human-readable aliases from public key mappings.
- Computes handshake duration against current monotonic and wall-clock epochs.

### 2. `PeerMonitor` (`wirepulse/monitor.py`)
- Stateful engine maintaining polling histories across consecutive scrape ticks.
- Computes instantaneous transmit (`tx_bytes_per_sec`) and receive (`rx_bytes_per_sec`) transfer throughput.
- Enforces debounce windows to prevent jitter and floating point division errors.

### 3. `PrometheusExporter` (`wirepulse/exporter.py`)
- Implements `http.server.BaseHTTPRequestHandler` with `ThreadingMixIn`.
- Serves Prometheus exposition text format directly via streaming buffers.
- Emits standard OpenMetrics gauge and counter schemas.
- Includes `/healthz` liveness/readiness probes for containerized and procd orchestrations.

### 4. `TerminalRenderer` & Live TUI (`wirepulse/tui.py`)
- Provides human-friendly terminal dashboard without relying on curses or ncurses C-libraries.
- ANSI-compliant formatting, auto-detecting terminal width and truncating long hashes gracefully.
