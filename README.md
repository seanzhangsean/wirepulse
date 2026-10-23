# WirePulse

<p align="center">
  <strong>Lightweight WireGuard telemetry daemon, live terminal monitor, and Prometheus exporter for edge gateways & OpenWrt.</strong>
</p>

<p align="center">
  <a href="https://github.com/seanzhangsean/wirepulse/actions"><img src="https://img.shields.io/badge/CI-Passing-brightgreen?style=flat-square" alt="CI"></a>
  <a href="https://github.com/seanzhangsean/wirepulse/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9+-informational.svg?style=flat-square" alt="Python 3.9+"></a>
  <a href="https://openwrt.org/"><img src="https://img.shields.io/badge/OpenWrt-Compatible-00A9CE?style=flat-square" alt="OpenWrt"></a>
  <a href="https://prometheus.io/"><img src="https://img.shields.io/badge/Prometheus-Exporter-E6522C?style=flat-square" alt="Prometheus"></a>
  <a href="https://github.com/seanzhangsean/wirepulse/stargazers"><img src="https://img.shields.io/github/stars/seanzhangsean/wirepulse?style=flat-square" alt="Stars"></a>
</p>

---

## Highlights

- ⚡ **Ultra-Low Resource Footprint**: Built purely with Python standard library constructs — **zero external dependencies** required to run. Uses less than **12MB RAM** on typical routers.
- 📊 **Native Prometheus Metrics**: Built-in HTTP server exposes standard OpenMetrics at `:9182/metrics` for scraping by Prometheus, VictoriaMetrics, or Grafana Agent.
- 🖥️ **Live Terminal Dashboard (`top`)**: Real-time console UI with transfer rates, handshake freshness, and connection status without needing curses or external C libs.
- 🏷️ **Human-Readable Peer Aliases**: Map cryptic WireGuard base64 public keys into descriptive names (e.g., `office-nas`, `alice-phone`).
- 🔄 **Throughput Delta Calculation**: Accurately tracks per-peer instantaneous Rx/Tx transfer rates (bytes/second) across polling intervals.
- 🛡️ **Embedded Linux & OpenWrt First**: Includes ready-to-use OpenWrt `procd` init scripts, UCI configuration files, and `/healthz` liveness endpoints.

---

## Architecture

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

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/seanzhangsean/wirepulse.git
cd wirepulse

# Optional: Install globally or run in place
pip install .
```

### 2. Inspect Interface Status

View a formatted table of all WireGuard interfaces and connected peers:

```bash
wirepulse status
```

Output:
```text
==================================================================================
 WirePulse v0.2.1 - WireGuard Telemetry Dashboard
==================================================================================
Interface: wg0        Port: 51820    Status: [3/4 peers active]
Public Key: 4tZ1k9v...qW8=
----------------------------------------------------------------------------------
PEER / ALIAS           ENDPOINT             HANDSHAKE    RX         TX         STATUS
----------------------------------------------------------------------------------
office-gateway         198.51.100.2:51820   14s ago      2.4 MiB    18.1 MiB   ONLINE
alice-macbook          203.0.113.44:51820   42s ago      840.2 KiB  1.1 MiB    ONLINE
backup-server          198.51.100.99:51820  1m 12s ago   140.5 MiB  98.2 MiB   ONLINE
stale-client           (none)               Never        0.0 B      0.0 B      IDLE  
----------------------------------------------------------------------------------
```

### 3. Launch Live Terminal Monitor

```bash
wirepulse top -n 2
```

### 4. Run Prometheus Exporter Daemon

```bash
wirepulse serve --port 9182 --interfaces wg0,wg1
```

Or query the metrics directly:
```bash
curl http://localhost:9182/metrics
```

---

## Prometheus Metrics Reference

| Metric Name | Type | Description |
|:---|:---|:---|
| `wireguard_build_info` | Gauge | Static version and build metadata |
| `wireguard_interface_peers_total` | Gauge | Total registered peers on interface |
| `wireguard_interface_active_peers` | Gauge | Number of peers with handshake within last 180s |
| `wireguard_peer_received_bytes_total` | Counter | Cumulative inbound bytes per peer |
| `wireguard_peer_transmitted_bytes_total` | Counter | Cumulative outbound bytes per peer |
| `wireguard_peer_last_handshake_seconds` | Gauge | Seconds elapsed since last completed handshake |
| `wireguard_peer_active` | Gauge | Binary flag: `1` if peer has completed handshake within 180s, `0` otherwise |
| `wireguard_peer_rx_bytes_per_second` | Gauge | Instantaneous inbound transfer throughput |
| `wireguard_peer_tx_bytes_per_second` | Gauge | Instantaneous outbound transfer throughput |

---

## Configuration (`wirepulse.json`)

WirePulse searches for configuration in `/etc/wirepulse/wirepulse.json` or can be specified via `-c /path/to/config.json`:

```json
{
  "interfaces": ["wg0"],
  "listen_address": "0.0.0.0",
  "listen_port": 9182,
  "poll_interval": 5,
  "metrics_path": "/metrics",
  "peer_aliases": {
    "HIjK567LmnOPqRstUVwXyz1234567890abcdef=": "office-gateway",
    "AbCdEf1234567890HIjK567LmnOPqRstUVwXyz=": "alice-macbook"
  }
}
```

Environment variables are also supported and take precedence:
- `WIREPULSE_INTERFACES`: Comma-delimited list of interfaces (e.g. `wg0,wg1`)
- `WIREPULSE_LISTEN_PORT`: Exporter port (e.g. `9182`)
- `WIREPULSE_LISTEN_ADDR`: Exporter bind address (e.g. `127.0.0.1`)

---

## OpenWrt Integration

WirePulse is specifically tailored to run on OpenWrt routers. See [docs/openwrt-setup.md](docs/openwrt-setup.md) for full details on:
- Setting up the OpenWrt `procd` init script
- Configuring UCI integration
- Firewall and routing considerations

---

## Development & Testing

Run unit tests with the standard Python test runner (no pip packages needed):

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## Roadmap

- [x] Pure standard-library parser for `wg show <interface> dump`
- [x] Multi-threaded HTTP Prometheus metrics server
- [x] Live TUI console dashboard (`top` command)
- [x] OpenWrt `procd` service script & packaging
- [ ] Direct netlink integration via Linux `GENL` socket (pure kernel bypass)
- [ ] Alerting webhooks on peer offline state transitions

---

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

Developed with care by **Sean Zhang** ([@seanzhangsean](https://github.com/seanzhangsean)).
