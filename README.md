# EDAO-NMS Onboarding Tool

**Version:** 1.1  
**Platform:** macOS (Apple Silicon / Intel) · Windows  
**Requires:** Python 3.9+  (no extra packages — uses only the standard library)

A cross-platform GUI tool that automates the full MSP / Customer / Site onboarding workflow in **Zabbix 7.x (EDAO-NMS)** via the Zabbix JSON-RPC API.

---

## What it does

The tool automates all 5 steps from the MSP Onboarding Guide:

| Step | Action | API method |
|------|--------|------------|
| 1 | Create Proxy | `proxy.create` |
| 2 | Create Host Groups (`MSP/{MSP}-Group/{Customer}` + `/{Site}`) | `hostgroup.create` |
| 3a | Create Discovery Rule | `drule.create` |
| 3b | Create Discovery Action (add host, assign groups, link templates, enable) | `action.create` |
| 4 | Mass-update hosts — assign group, proxy, lat/lon inventory | `host.massadd` · `host.massupdate` |
| 5 | Configure PSK encryption on proxy (post-installation) | `proxy.update` |

---

## Naming Conventions

| Object | Format | Example |
|--------|--------|---------|
| Proxy | `Proxy{MSP}{Customer}-{Site}` | `ProxyEDAOAcme-NYC` |
| Host Group 1 | `MSP/{MSP}-Group/{Customer}` | `MSP/EDAO-Group/Acme` |
| Host Group 2 | `MSP/{MSP}-Group/{Customer}/{Site}` | `MSP/EDAO-Group/Acme/NYC` |
| Discovery Rule | `Proxy-{Customer}-{Site}` | `Proxy-Acme-NYC` |
| Discovery Action | `Discovery{Customer}-{Site}` | `DiscoveryAcme-NYC` |

---

## Setup

### macOS (Apple Silicon / Intel)

1. Install Python 3.9+ if not already present:
   ```bash
   brew install python3
   # or download from https://python.org
   ```
2. Double-click **`launch_mac.command`**  
   *(first time: right-click → Open if Gatekeeper blocks it)*

### Windows

1. Install Python 3.9+ from [python.org](https://python.org) — check **"Add to PATH"**
2. Double-click **`launch_windows.bat`**

### Run directly
```bash
python3 edao_onboard.py
```

---

## Authentication

The tool supports two authentication methods:

### API Token (recommended)
1. In Zabbix UI → top-right username → **API tokens**
2. Click **Create API token** — set no expiry for a permanent token
3. Paste the token into the **Connection** tab → **API Token** field

### Username / Password
Enter Zabbix credentials directly.  
> **Note:** Zabbix blocks the account after 5 failed attempts. Use the API Token method if you hit lockout issues.

---

## Tabs

### 🔌 Connection
- Set server URL, choose auth method, test connection.
- URL and username are saved between sessions.

### 🏢 Onboarding
Fill in:
- **MSP Name** — e.g. `EDAO`
- **MSP Group Label** — auto-filled as `{MSP}-Group`, editable
- **Customer Name** — e.g. `Acme`
- **Site Name** — e.g. `NYC`
- **Proxy Public IP** — public IP of the on-site proxy
- **IP Range** — subnet for discovery (e.g. `192.168.1.0/24`)
- **Discovery Checks** — ICMP Ping, SNMP (v1), Zabbix Agent
- **Location** — latitude / longitude for inventory
- **Templates** — fetch and multi-select templates to link

Live preview updates all object names as you type.  
Click **▶ Run Full Onboarding** — a confirmation dialog shows exactly what will be created.

### 🖥 Hosts
Search discovered hosts by name/IP or host group.  
Multi-select from the sortable results table, then mass-update:
- Add to a host group (additive — never removes existing groups)
- Assign a monitoring proxy
- Set location lat/lon in inventory

### 🔐 PSK Config
After the proxy is physically installed on-site:
1. Select the proxy from the dropdown
2. Enter the PSK Identity and PSK hex from the EDAO Control Hub TXT file  
   *(or click **Browse TXT File…** to auto-import)*
3. Click **🔐 Apply PSK Encryption**

---

## Activity Log

All API calls and results are shown in the dark log panel at the bottom.  
Color coding: `teal` = success, `yellow` = warning / skipped, `red` = error.

---

## Files

| File | Description |
|------|-------------|
| `edao_onboard.py` | Main application |
| `launch_mac.command` | macOS double-click launcher |
| `launch_windows.bat` | Windows double-click launcher |
| `README.md` | This file |

---

## Release History

### v1.1 — 2026-04-30
- Added API Token authentication (bypasses brute-force lockout)
- Added MSP Group Label field (auto-fills as `{MSP}-Group`)
- Fixed host group path to use `{MSP}-Group` convention
- Fixed discovery action naming to `Discovery{Customer}-{Site}`
- Fixed action condition to type 18 only (matches live server)
- Fixed SNMP check to SNMPv1 type 10 (matches live discovery rules)
- Added Zabbix Agent check enabled by default
- Added full **Hosts** tab — search, multi-select, mass update (group / proxy / location)

### v1.0 — 2026-04-30
- Initial release
- Steps 1–3 + PSK Config (Steps 1, 2, 3a, 3b, 5)

---

## Security Notes

- The API token is stored in memory only during the session — never written to disk.
- Local config (`~/.edao_onboard_config.json`) saves only the server URL and username — never passwords or tokens.
- TLS certificate verification is relaxed to support self-signed certs on internal NMS servers.
