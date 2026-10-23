# Deploying WirePulse on OpenWrt

This guide walks through deploying and configuring WirePulse on OpenWrt 21.02, 22.03, 23.05, and newer snapshots.

---

## 1. Prerequisites

Ensure Python 3 and the WireGuard tools are installed on your OpenWrt router:

```sh
opkg update
opkg install python3-light wireguard-tools
```

---

## 2. Installation

### Option A: From PyPI / Pip
```sh
pip install wirepulse
```

### Option B: Standalone Script / Package
Clone or copy the repository onto the router:
```sh
mkdir -p /opt/wirepulse
git clone https://github.com/seanzhangsean/wirepulse.git /opt/wirepulse
ln -s /opt/wirepulse/wirepulse/cli.py /usr/bin/wirepulse
chmod +x /usr/bin/wirepulse
```

---

## 3. Configuration

Create `/etc/wirepulse/wirepulse.json`:

```json
{
  "interfaces": ["wg0"],
  "listen_address": "0.0.0.0",
  "listen_port": 9182,
  "poll_interval": 5,
  "peer_aliases": {
    "uXg5829aBcdfE450123...=": "Sean-Laptop",
    "bLm901a1Zcv...=": "Home-NAS"
  }
}
```

---

## 4. Setting Up the Procd Service

Install the service script:

```sh
cp openwrt/etc/init.d/wirepulse /etc/init.d/wirepulse
chmod +x /etc/init.d/wirepulse
/etc/init.d/wirepulse enable
/etc/init.d/wirepulse start
```

Verify service status:
```sh
/etc/init.d/wirepulse status
curl http://127.0.0.1:9182/metrics
```

---

## 5. Prometheus Scraping Configuration

Add the following scrape target to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "openwrt-wireguard"
    scrape_interval: 10s
    static_configs:
      - targets: ["192.168.1.1:9182"]
        labels:
          router: "openwrt-main"
```
