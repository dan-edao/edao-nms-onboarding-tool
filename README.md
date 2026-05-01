# EDAO-NMS Onboarding Tool

**Version:** 2.6  
**Platform:** macOS (Apple Silicon / Intel) · Windows  
**Requires:** Python 3.9+  (no extra packages — uses only the standard library)

A cross-platform GUI tool that automates the full MSP / Customer / Site onboarding workflow in **EDAO-NMS (Zabbix 7.x)** via the Zabbix JSON-RPC API.

---

## What it does

The tool automates all 5 steps from the MSP Onboarding Guide:

| Step | Action | API method |
|------|--------|------------|
| 1 | Create Proxy | `proxy.create` |
| 2 | Create Host Groups (`MSP/{MSP}/{Customer}` + `/{Site}`) | `hostgroup.create` |
| 3a | Create Discovery Rule | `drule.create` |
| 3b | Create Discovery Action (add host, assign groups, link templates, enable) | `action.create` |
| 4 | Mass-update hosts — assign group, proxy, lat/lon inventory | `host.massadd` · `host.massupdate` |
| 5 | Configure PSK encryption on proxy (post-installation) | `proxy.update` |

---

## Naming Conventions

| Object | Format | Example (MSP=EDAO, Customer=Acme, Site=NYC) |
|--------|--------|------|
| Proxy | `Proxy{Customer}{Site}` | `ProxyAcmeNYC` |
| Host Group 1 | `MSP/{MSP}/{Customer}` | `MSP/EDAO/Acme` |
| Host Group 2 | `MSP/{MSP}/{Customer}/{Site}` | `MSP/EDAO/Acme/NYC` |
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

Enter your **EDAO-NMS username and password** — the same credentials you use to log into the EDAO-NMS web interface. The account must have Super Admin role with API access enabled.

> **Account blocked?** EDAO-NMS blocks an account after 5 failed login attempts.  
> To unblock: log into the web UI as a different admin → Administration → Users → find the user → **Unblock**.  
> Alternatively, expand **Advanced (API Token)** on the Connection tab and paste an API token to bypass the lockout.

### Creating an API Token (optional fallback)
1. In EDAO-NMS UI → top-right username → **API tokens**
2. Click **Create API token** — set no expiry for a permanent token
3. Paste the token into the **Advanced (API Token)** field on the Connection tab

---

## Tabs

### 🔌 Connection
- Set server URL, enter username/password, test connection.
- URL and username are saved between sessions.
- **Advanced** section: paste an API Token as a fallback if the account is blocked.

### 🏢 Onboarding
Fill in:
- **MSP Name** — e.g. `EDAO`
- **Customer Name** — e.g. `Acme`
- **Site Name** — e.g. `NYC`
- **Proxy Public IP** — public IP of the on-site proxy
- **IP Range** — subnet for discovery (e.g. `192.168.1.0/24`)
- **Discovery Checks** — ICMP Ping, SNMP (v1), EDAO-NMS Agent
- **Location** — latitude / longitude for inventory
- **Templates** — fetch and multi-select templates to link (defaults to `EDAO-ICMP Ping`)

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

### v2.6 — 2026-04-30
- Fix: SNMP discovery check OID now uses correct field name `key_` (not `snmp_oid`) per Zabbix 7.x dcheck API

### v2.5 — 2026-04-30
- Fix: SNMP discovery check now includes required `snmp_oid` (sysDescr 1.3.6.1.2.1.1.1.0)
- Fix: NameError crash in error handler lambda (Python 3 exception variable scope)

### v2.4 — 2026-04-30
- Fix proxy creation error on Zabbix 7.x: active proxies now use address="127.0.0.1" (required by API); public IP stored in proxy description

### v2.3 — 2026-04-30
- Connection tab redesigned: content centred, tighter layout
- Onboarding tab: reduced section/field spacing for less scrolling
- Template filter now starts empty (shows all templates after fetch)
- Multi-select hint updated to be clearer

### v2.2 — 2026-04-30
- PSK Encryption moved into Onboarding tab (section 3) — no more separate PSK Config tab
- Run Full Onboarding now includes PSK as Step 5 (skipped gracefully if fields are empty)
- Template list now has a live filter box (default: "EDAO") with a Clear button
- "IP Range" label renamed to "Monitoring Subnet"
- Location (Inventory) latitude/longitude fields removed

### v2.0 — 2026-04-30
- Connection tab: New Site / Existing Site selector after connecting
  - **New Site** → navigates to full Onboarding tab (create proxy, groups, discovery)
  - **Existing Site** → hides Onboarding tab, navigates directly to PSK Config

### v1.9 — 2026-04-30
- PSK Config tab: proxy is no longer a manual dropdown — it reads automatically from the Onboarding tab (Customer + Site name) and updates live as you type
- Removed the proxy Refresh button from PSK tab

### v1.8 — 2026-04-30
- Removed username/password auth entirely — API Token only
- Connection tab simplified: Server URL + API Token field
- Save / Replace / Clear Token buttons; token persists across sessions

### v1.7 — 2026-04-30
- Fixed crash: `EXTENDED` import removed accidentally in v1.6, restored
- Connection tab: Auth Method radio (Username/Password vs API Token)
- API Token can now be saved to disk and reloaded on next launch
- Save Token / Replace Token / Clear Token buttons on Connection tab
- Blocked-account hint now points to the API Token tab option

### v1.6 — 2026-04-30
- Removed Hosts tab — discovery action automatically handles all host assignments
- Tool is now 3 tabs: Connection → Onboarding → PSK Config

### v1.5 — 2026-04-30
- Removed logo from header
- Header now shows centered 2-line text: EDAO / NMS Onboarding Tool
- All files versioned together for consistent tracking

### v1.4 — 2026-04-30
- Connect button disables during login to prevent repeat attempts that trigger brute-force lockout
- Blocked-account error now shows step-by-step unblock instructions
- Added collapsible **Advanced (API Token)** section as a lockout bypass fallback

### v1.3 — 2026-04-30
- Header redesigned: centered 2-line title (EDAO / NMS Onboarding Tool) with logo
- API Token auth option removed — username/password only (matching EDAO-NMS web login)
- All "Zabbix" UI labels replaced with "EDAO-NMS"
- MSP Group Label field removed — group paths now `MSP/{MSP}/{Customer}/{Site}`
- Proxy naming simplified to `Proxy{Customer}{Site}` (no MSP prefix)
- Templates list auto-selects "EDAO-ICMP Ping" after fetch

### v1.2 — 2026-04-30
- Increased all font sizes for readability
- Embedded EDAO Group logo in banner
- Expanded minimum window size to 900×760

### v1.1 — 2026-04-30
- Added API Token authentication (bypasses brute-force lockout)
- Added MSP Group Label field (auto-fills as `{MSP}-Group`)
- Fixed discovery action naming to `Discovery{Customer}-{Site}`
- Fixed action condition to type 18 only
- Fixed SNMP check to SNMPv1 type 10
- Added Zabbix Agent check enabled by default
- Added full **Hosts** tab — search, multi-select, mass update (group / proxy / location)

### v1.0 — 2026-04-30
- Initial release — Steps 1–3 + PSK Config

---

## Security Notes

- Credentials are held in memory only during the session — never written to disk.
- Local config (`~/.edao_onboard_config.json`) saves only the server URL and username — never passwords or tokens.
- TLS certificate verification is relaxed to support self-signed certs on internal NMS servers.
