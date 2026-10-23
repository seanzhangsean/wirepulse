# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.1] - 2026-10-20

### Added
- OpenWrt procd service script and UCI configuration template (`openwrt/etc/init.d/wirepulse`).
- `/healthz` HTTP probe endpoint for container and process orchestrators.
- Automated CI matrix testing on Python 3.9 through 3.13.

### Improved
- Memory footprint optimization on embedded systems (<12MB RAM).
- Graceful handling of inactive or disconnected peers in Prometheus exposition.

---

## [0.2.0] - 2026-09-15

### Added
- Interactive live terminal UI (`wirepulse top`) with auto-refreshing stats.
- Dynamic peer transfer rate estimation (Rx/Tx bytes per second).
- Friendly alias resolution via `wirepulse.json` config.
- One-shot status inspection with optional JSON export (`wirepulse status --json`).

---

## [0.1.0] - 2026-08-01

### Added
- Initial release.
- Core WireGuard `wg show dump` parser.
- Built-in multi-threaded Prometheus exposition server (`/metrics`).
- CLI framework with diagnostic checks (`wirepulse check`).
