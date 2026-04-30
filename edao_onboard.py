#!/usr/bin/env python3
"""
EDAO-NMS Onboarding Tool v1.1
Automates MSP/Customer/Site onboarding in Zabbix 7.x via API.
Cross-platform: macOS (Apple Silicon) and Windows.
"""

import json
import os
import re
import ssl
import threading
import urllib.error
import urllib.request
from datetime import datetime
from typing import Optional
from tkinter import (
    END, EXTENDED, LEFT, RIGHT, BOTH, X, Y, W, E, N, S,
    BooleanVar, StringVar,
    filedialog, messagebox, scrolledtext,
)
import tkinter as tk
import tkinter.ttk as ttk

DEFAULT_URL  = "https://edaonms.edaogroup.io"
CONFIG_PATH  = os.path.expanduser("~/.edao_onboard_config.json")


# ══════════════════════════════════════════════════════════════════════════════
# Zabbix API client  (Zabbix 7.x — Bearer-token auth)
# ══════════════════════════════════════════════════════════════════════════════

class ZabbixAPI:
    def __init__(self, url: str):
        self.url  = url.rstrip("/") + "/api_jsonrpc.php"
        self.auth: Optional[str] = None
        self._id  = 0
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode    = ssl.CERT_NONE

    def _request(self, method: str, params) -> object:
        self._id += 1
        payload = json.dumps({
            "jsonrpc": "2.0", "method": method,
            "params": params, "id": self._id,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if self.auth:
            headers["Authorization"] = f"Bearer {self.auth}"
        req = urllib.request.Request(self.url, data=payload, headers=headers)
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=20) as r:
                resp = json.loads(r.read())
        except urllib.error.URLError as e:
            raise ConnectionError(f"Network error: {e.reason}")
        if "error" in resp:
            err = resp["error"]
            raise RuntimeError(err.get("data") or err.get("message") or "Unknown API error")
        return resp["result"]

    def call(self, method: str, params=None, **kwargs) -> object:
        if params is None:
            params = kwargs
        return self._request(method, params)

    # ── auth ──────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> str:
        self.auth = self._request("user.login",
                                  {"username": username, "password": password})
        return self.auth

    def use_token(self, token: str):
        """Use a pre-generated Zabbix API token directly."""
        self.auth = token

    def logout(self):
        try:
            self._request("user.logout", [])
        except Exception:
            pass
        self.auth = None

    def api_version(self) -> str:
        return self._request("apiinfo.version", {})

    # ── helpers ───────────────────────────────────────────────────────────

    def get_or_create_hostgroup(self, name: str) -> str:
        existing = self.call("hostgroup.get",
                             filter={"name": [name]}, output=["groupid"])
        if existing:
            return existing[0]["groupid"]
        return self.call("hostgroup.create", name=name)["groupids"][0]

    def get_proxy_id(self, name: str) -> Optional[str]:
        r = self.call("proxy.get", filter={"name": [name]}, output=["proxyid"])
        return r[0]["proxyid"] if r else None

    def get_drule_id(self, name: str) -> Optional[str]:
        r = self.call("drule.get", filter={"name": [name]}, output=["druleid"])
        return r[0]["druleid"] if r else None


# ══════════════════════════════════════════════════════════════════════════════
# Onboarding logic
# ══════════════════════════════════════════════════════════════════════════════

class Onboarder:
    def __init__(self, api: ZabbixAPI, log):
        self.api = api
        self.log = log   # callable(msg, level)

    def _log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log(f"[{ts}] [{level}] {msg}", level)

    # ── Step 1: Proxy ─────────────────────────────────────────────────────

    def create_proxy(self, msp: str, customer: str, site: str, ip: str) -> str:
        name = f"Proxy{msp}{customer}-{site}"
        existing = self.api.get_proxy_id(name)
        if existing:
            self._log(f"Proxy '{name}' already exists (id={existing}), skipping.", "WARN")
            return existing
        result = self.api.call("proxy.create",
            name=name, operating_mode=0, address=ip, port="10051")
        pid = result["proxyids"][0]
        self._log(f"Created proxy '{name}'  (id={pid}, ip={ip})")
        return pid

    # ── Step 2: Host groups ───────────────────────────────────────────────

    def create_host_groups(self, msp: str, msp_group: str,
                           customer: str, site: str) -> tuple:
        # msp_group = "EDAO-Group",  e.g.  MSP/EDAO-Group/Customer/Site
        g1 = f"MSP/{msp_group}/{customer}"
        g2 = f"MSP/{msp_group}/{customer}/{site}"
        gid1 = self.api.get_or_create_hostgroup(g1)
        self._log(f"Host group '{g1}'  (id={gid1})")
        gid2 = self.api.get_or_create_hostgroup(g2)
        self._log(f"Host group '{g2}'  (id={gid2})")
        return gid1, gid2

    # ── Step 3a: Discovery rule ───────────────────────────────────────────

    def create_discovery_rule(self, customer: str, site: str, proxy_id: str,
                               ip_range: str, use_icmp: bool, use_snmp: bool,
                               snmp_community: str, use_agent: bool) -> str:
        name = f"Proxy-{customer}-{site}"
        existing = self.api.get_drule_id(name)
        if existing:
            self._log(f"Discovery rule '{name}' already exists, skipping.", "WARN")
            return existing

        dchecks = []
        if use_icmp:
            dchecks.append({"type": "12"})                    # ICMP ping
        if use_snmp:
            dchecks.append({                                   # SNMPv1  (matches live convention)
                "type": "10",
                "snmp_community": snmp_community or "public",
                "ports": "161",
            })
        if use_agent:
            dchecks.append({                                   # Zabbix agent
                "type": "9", "key_": "system.hostname", "ports": "10050",
            })
        if not dchecks:
            dchecks.append({"type": "12"})

        result = self.api.call("drule.create",
            name=name, iprange=ip_range, delay="5m",
            proxyid=proxy_id, dchecks=dchecks)
        did = result["druleids"][0]
        self._log(f"Created discovery rule '{name}'  (id={did}, range={ip_range})")
        return did

    # ── Step 3b: Discovery action ─────────────────────────────────────────

    def create_discovery_action(self, customer: str, site: str, drule_id: str,
                                 gid1: str, gid2: str, template_ids: list) -> str:
        # Naming convention from live data:  Discovery{Customer}-{Site}
        action_name = f"Discovery{customer}-{site}"
        existing = self.api.call("action.get",
            filter={"name": [action_name]}, output=["actionid"])
        if existing:
            self._log(f"Discovery action '{action_name}' already exists, skipping.", "WARN")
            return existing[0]["actionid"]

        operations = [
            {"operationtype": 2},                                       # Add host
            {"operationtype": 4, "opgroup": [{"groupid": gid1}]},      # Add to group 1
            {"operationtype": 4, "opgroup": [{"groupid": gid2}]},      # Add to group 2
            {"operationtype": 8},                                       # Enable host
        ]
        for tid in template_ids:
            operations.append({
                "operationtype": 6,
                "optemplate": [{"templateid": tid}],
            })

        result = self.api.call("action.create",
            name=action_name,
            eventsource=1,          # Discovery
            status=0,               # Enabled
            filter={
                "evaltype": 0,
                "conditions": [{    # Match only this discovery rule  (type 18)
                    "conditiontype": 18, "operator": 0, "value": str(drule_id),
                }],
            },
            operations=operations,
        )
        aid = result["actionids"][0]
        self._log(f"Created discovery action '{action_name}'  (id={aid})")
        return aid

    # ── Step 4: Mass-update hosts ─────────────────────────────────────────

    def mass_update_hosts(self, host_ids: list, add_group_id: Optional[str],
                          proxy_id: Optional[str], latitude: str, longitude: str):
        if not host_ids:
            self._log("No hosts selected — nothing to update.", "WARN")
            return
        hosts_param = [{"hostid": h} for h in host_ids]
        n = len(host_ids)

        if add_group_id:
            self.api.call("host.massadd",
                hosts=hosts_param, groups=[{"groupid": add_group_id}])
            self._log(f"Added {n} host(s) to group id={add_group_id}")

        update = {"hosts": hosts_param}
        if proxy_id:
            update["monitored_by"] = 1
            update["proxyid"]      = proxy_id
        if latitude and longitude:
            update["inventory_mode"] = 0
            update["inventory"] = {
                "location_lat": latitude,
                "location_lon": longitude,
            }
        if len(update) > 1:
            self.api.call("host.massupdate", update)
            parts = []
            if proxy_id:               parts.append(f"proxy id={proxy_id}")
            if latitude and longitude: parts.append(f"location ({latitude}, {longitude})")
            self._log(f"Updated {n} host(s): {', '.join(parts)}")

        self._log(f"Mass update complete for {n} host(s).", "OK")

    # ── Step 5: PSK encryption ────────────────────────────────────────────

    def configure_psk(self, proxy_id: str, psk_identity: str, psk: str):
        self.api.call("proxy.update",
            proxyid=proxy_id, tls_accept=4, tls_connect=4,
            tls_psk_identity=psk_identity, tls_psk=psk)
        self._log(f"PSK encryption configured on proxy id={proxy_id}")

    # ── Full onboarding run ───────────────────────────────────────────────

    def run(self, msp: str, msp_group: str, customer: str, site: str,
            proxy_ip: str, ip_range: str,
            use_icmp: bool, use_snmp: bool, snmp_community: str, use_agent: bool,
            template_ids: list, latitude: str, longitude: str) -> dict:
        r = {}
        self._log("═" * 52)
        self._log(f"Onboarding  MSP={msp}  Customer={customer}  Site={site}")

        self._log("── Step 1: Create Proxy ─────────────────────────")
        r["proxy_id"] = self.create_proxy(msp, customer, site, proxy_ip)

        self._log("── Step 2: Create Host Groups ───────────────────")
        r["gid1"], r["gid2"] = self.create_host_groups(msp, msp_group, customer, site)

        self._log("── Step 3a: Create Discovery Rule ───────────────")
        r["drule_id"] = self.create_discovery_rule(
            customer, site, r["proxy_id"], ip_range,
            use_icmp, use_snmp, snmp_community, use_agent)

        self._log("── Step 3b: Create Discovery Action ─────────────")
        r["action_id"] = self.create_discovery_action(
            customer, site, r["drule_id"], r["gid1"], r["gid2"], template_ids)

        self._log("═" * 52)
        self._log("Onboarding complete!", "OK")
        self._log(f"  Proxy       : Proxy{msp}{customer}-{site}   (id={r['proxy_id']})")
        self._log(f"  Group 1     : MSP/{msp_group}/{customer}    (id={r['gid1']})")
        self._log(f"  Group 2     : MSP/{msp_group}/{customer}/{site}  (id={r['gid2']})")
        self._log(f"  Disc. rule  : Proxy-{customer}-{site}       (id={r['drule_id']})")
        self._log(f"  Disc. action: Discovery{customer}-{site}    (id={r['action_id']})")
        if latitude and longitude:
            self._log(f"  Location    : {latitude}, {longitude}  "
                      "(apply via Hosts tab → Mass Update)")
        self._log("Next: use the Hosts tab to mass-assign discovered hosts.")
        self._log("Then: install proxy on-site and apply PSK via the PSK Config tab.")
        return r


# ══════════════════════════════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════════════════════════════

FONT_LABEL  = ("Helvetica", 12)
FONT_ENTRY  = ("Helvetica", 12)
FONT_LOG    = ("Courier",   11)
FONT_HEAD   = ("Helvetica", 14, "bold")
FONT_SMALL  = ("Helvetica", 10)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EDAO-NMS Onboarding Tool  v1.1")
        self.resizable(True, True)
        self.minsize(820, 700)

        self.api: Optional[ZabbixAPI]  = None
        self._connected                = False
        self._templates: list          = []
        self._onboard_results: Optional[dict] = None
        self._host_rows: list          = []
        self._host_groups_all: list    = []
        self._proxies_all: list        = []

        self._build_ui()
        self._load_config()

    # ── Config ────────────────────────────────────────────────────────────

    def _load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                cfg = json.loads(open(CONFIG_PATH).read())
                self._url_var.set(cfg.get("url",      DEFAULT_URL))
                self._user_var.set(cfg.get("username", "dan@edaogroup.io"))
                self._auth_mode.set(cfg.get("auth_mode", "userpass"))
            except Exception:
                pass

    def _save_config(self):
        try:
            json.dump({
                "url":       self._url_var.get(),
                "username":  self._user_var.get(),
                "auth_mode": self._auth_mode.get(),
            }, open(CONFIG_PATH, "w"))
        except Exception:
            pass

    # ── Main UI ───────────────────────────────────────────────────────────

    def _build_ui(self):
        banner = tk.Frame(self, bg="#003366")
        banner.pack(fill=X)
        tk.Label(banner, text="  EDAO-NMS  Onboarding Tool",
                 bg="#003366", fg="white",
                 font=("Helvetica", 16, "bold"), pady=10).pack(side=LEFT)
        self._status_lbl = tk.Label(banner, text="● Not connected",
                                    bg="#003366", fg="#FF6B6B",
                                    font=("Helvetica", 11))
        self._status_lbl.pack(side=RIGHT, padx=12)

        nb = ttk.Notebook(self)
        nb.pack(fill=BOTH, expand=True, padx=8, pady=8)

        self._tab_connect = ttk.Frame(nb)
        self._tab_onboard = ttk.Frame(nb)
        self._tab_hosts   = ttk.Frame(nb)
        self._tab_psk     = ttk.Frame(nb)

        nb.add(self._tab_connect, text="  🔌 Connection  ")
        nb.add(self._tab_onboard, text="  🏢 Onboarding  ")
        nb.add(self._tab_hosts,   text="  🖥  Hosts  ")
        nb.add(self._tab_psk,     text="  🔐 PSK Config  ")

        self._build_connect_tab()
        self._build_onboard_tab()
        self._build_hosts_tab()
        self._build_psk_tab()

        ttk.Separator(self, orient="horizontal").pack(fill=X, padx=8)
        log_frame = ttk.LabelFrame(self, text="  Activity Log", padding=4)
        log_frame.pack(fill=BOTH, expand=False, padx=8, pady=(4, 8))
        self._log_box = scrolledtext.ScrolledText(
            log_frame, height=10, font=FONT_LOG, state="disabled",
            wrap="word", bg="#1e1e1e", fg="#d4d4d4")
        self._log_box.pack(fill=BOTH, expand=True)
        ttk.Button(log_frame, text="Clear Log",
                   command=self._clear_log).pack(anchor=E, pady=(2, 0))

        self._log_box.tag_config("INFO", foreground="#d4d4d4")
        self._log_box.tag_config("OK",   foreground="#4ec9b0")
        self._log_box.tag_config("WARN", foreground="#dcdcaa")
        self._log_box.tag_config("ERR",  foreground="#f44747")

    # ── Connection tab ────────────────────────────────────────────────────

    def _build_connect_tab(self):
        f = self._tab_connect
        tk.Label(f, text="Zabbix Server Connection",
                 font=FONT_HEAD).grid(row=0, column=0, columnspan=3,
                                      sticky=W, padx=16, pady=(16, 8))

        self._url_var   = StringVar(value=DEFAULT_URL)
        self._auth_mode = StringVar(value="userpass")   # "token" | "userpass"

        # Server URL
        tk.Label(f, text="Server URL:", font=FONT_LABEL, anchor=E).grid(
            row=1, column=0, sticky=E, padx=(16, 6), pady=6)
        ttk.Entry(f, textvariable=self._url_var,
                  font=FONT_ENTRY, width=44).grid(
            row=1, column=1, columnspan=2, sticky=W, pady=6)

        # Auth mode radio
        mode_frame = tk.Frame(f)
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=W, padx=16, pady=(8, 2))
        tk.Label(mode_frame, text="Auth method:", font=FONT_LABEL).pack(side=LEFT, padx=(0, 12))
        ttk.Radiobutton(mode_frame, text="API Token",
                        variable=self._auth_mode, value="token",
                        command=self._toggle_auth_mode).pack(side=LEFT, padx=6)
        ttk.Radiobutton(mode_frame, text="Username / Password",
                        variable=self._auth_mode, value="userpass",
                        command=self._toggle_auth_mode).pack(side=LEFT, padx=6)

        # Token row
        self._token_frame = tk.Frame(f)
        self._token_frame.grid(row=3, column=0, columnspan=3, sticky=W+E, padx=16, pady=4)
        tk.Label(self._token_frame, text="API Token:",
                 font=FONT_LABEL, anchor=E, width=14).pack(side=LEFT)
        self._token_var = StringVar()
        ttk.Entry(self._token_frame, textvariable=self._token_var,
                  font=FONT_ENTRY, width=52, show="*").pack(side=LEFT, padx=6)
        ttk.Button(self._token_frame, text="👁 Show/Hide",
                   command=self._toggle_token_vis).pack(side=LEFT)
        self._token_shown = False

        # User/pass rows (hidden initially)
        self._userpass_frame = tk.Frame(f)
        self._userpass_frame.grid(row=4, column=0, columnspan=3,
                                   sticky=W+E, padx=16, pady=4)
        self._user_var = StringVar(value="dan@edaogroup.io")
        self._pwd_var  = StringVar()
        for i, (lbl, var, hide) in enumerate([
            ("Username:", self._user_var, False),
            ("Password:", self._pwd_var,  True),
        ]):
            tk.Label(self._userpass_frame, text=lbl,
                     font=FONT_LABEL, anchor=E, width=14).grid(
                row=i, column=0, sticky=E, pady=4)
            ttk.Entry(self._userpass_frame, textvariable=var,
                      font=FONT_ENTRY, width=40,
                      show="*" if hide else "").grid(
                row=i, column=1, sticky=W, padx=6, pady=4)

        # Buttons
        btn_frame = tk.Frame(f)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=16)
        ttk.Button(btn_frame, text="Test & Connect",
                   command=self._do_connect).pack(side=LEFT, padx=8)
        ttk.Button(btn_frame, text="Disconnect",
                   command=self._do_disconnect).pack(side=LEFT, padx=8)

        # Info box
        info = ttk.LabelFrame(f, text="  ℹ  Connection Info", padding=8)
        info.grid(row=6, column=0, columnspan=3,
                  sticky=W+E, padx=16, pady=8)
        self._api_info_lbl = tk.Label(info, text="Not connected.",
                                      font=FONT_SMALL, justify=LEFT, anchor=W)
        self._api_info_lbl.grid(row=0, column=0, sticky=W)
        f.columnconfigure(1, weight=1)

        self._toggle_auth_mode()   # set initial visibility

    def _toggle_auth_mode(self):
        if self._auth_mode.get() == "token":
            self._token_frame.grid()
            self._userpass_frame.grid_remove()
        else:
            self._token_frame.grid_remove()
            self._userpass_frame.grid()

    def _toggle_token_vis(self):
        e = self._token_frame.winfo_children()[1]   # the Entry widget
        self._token_shown = not self._token_shown
        e.configure(show="" if self._token_shown else "*")

    # ── Onboarding tab ────────────────────────────────────────────────────

    def _build_onboard_tab(self):
        f = self._tab_onboard

        canvas = tk.Canvas(f, borderwidth=0, highlightthickness=0)
        vsb    = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        inner = tk.Frame(canvas)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        row = 0

        def section(title):
            nonlocal row
            tk.Label(inner, text=title, font=FONT_HEAD, anchor=W).grid(
                row=row, column=0, columnspan=3, sticky=W, padx=16, pady=(16, 4))
            ttk.Separator(inner, orient="horizontal").grid(
                row=row+1, column=0, columnspan=3,
                sticky=W+E, padx=16, pady=(0, 8))
            row += 2

        def field(label, var, hint="", width=30):
            nonlocal row
            tk.Label(inner, text=label, font=FONT_LABEL, anchor=E).grid(
                row=row, column=0, sticky=E, padx=(16, 6), pady=5)
            ttk.Entry(inner, textvariable=var,
                      font=FONT_ENTRY, width=width).grid(
                row=row, column=1, sticky=W, pady=5)
            if hint:
                tk.Label(inner, text=hint, font=FONT_SMALL, fg="#888").grid(
                    row=row, column=2, sticky=W, padx=6)
            row += 1

        # ── Section 1: Customer Info ──
        section("1 · Customer Info")
        self._msp_var       = StringVar()
        self._msp_group_var = StringVar()   # e.g. "EDAO-Group"
        self._customer_var  = StringVar()
        self._site_var      = StringVar()

        field("MSP Name:",        self._msp_var,      "e.g.  EDAO")
        field("MSP Group Label:", self._msp_group_var,
              "auto-filled as  {MSP}-Group  — edit if needed")
        field("Customer Name:",   self._customer_var,  "e.g.  Acme")
        field("Site Name:",       self._site_var,      "e.g.  NYC")

        # Auto-fill MSP Group when MSP changes
        self._msp_var.trace_add("write", self._autofill_msp_group)

        # Live preview
        self._preview_var = StringVar(value="—")
        tk.Label(inner, text="Preview:", font=FONT_LABEL, anchor=E).grid(
            row=row, column=0, sticky=E, padx=(16, 6), pady=5)
        tk.Label(inner, textvariable=self._preview_var,
                 font=("Courier", 11), fg="#007acc",
                 anchor=W, justify=LEFT).grid(
            row=row, column=1, columnspan=2, sticky=W, pady=5)
        row += 1
        for v in (self._msp_var, self._msp_group_var,
                  self._customer_var, self._site_var):
            v.trace_add("write", lambda *_: self._update_preview())

        # ── Section 2: Network ──
        section("2 · Network")
        self._proxy_ip_var = StringVar()
        self._ip_range_var = StringVar()
        field("Proxy Public IP:", self._proxy_ip_var, "e.g.  203.0.113.10")
        field("IP Range:",        self._ip_range_var,
              "e.g.  192.168.1.0/24   or   192.168.1.1-50")

        # ── Section 3: Discovery Checks ──
        section("3 · Discovery Checks")
        self._use_icmp  = BooleanVar(value=True)
        self._use_snmp  = BooleanVar(value=True)
        self._snmp_comm = StringVar(value="public")
        self._use_agent = BooleanVar(value=True)

        chk = tk.Frame(inner)
        chk.grid(row=row, column=0, columnspan=3, sticky=W, padx=16, pady=4)
        ttk.Checkbutton(chk, text="ICMP Ping",
                        variable=self._use_icmp).pack(side=LEFT, padx=8)
        ttk.Checkbutton(chk, text="SNMP (v1)",
                        variable=self._use_snmp,
                        command=self._toggle_snmp).pack(side=LEFT, padx=8)
        ttk.Checkbutton(chk, text="Zabbix Agent",
                        variable=self._use_agent).pack(side=LEFT, padx=8)
        row += 1

        tk.Label(inner, text="SNMP Community:",
                 font=FONT_LABEL, anchor=E).grid(
            row=row, column=0, sticky=E, padx=(16, 6), pady=5)
        self._snmp_entry = ttk.Entry(inner, textvariable=self._snmp_comm,
                                     font=FONT_ENTRY, width=20)
        self._snmp_entry.grid(row=row, column=1, sticky=W, pady=5)
        row += 1

        # ── Section 4: Location ──
        section("4 · Location  (Inventory)")
        self._lat_var = StringVar()
        self._lng_var = StringVar()
        field("Latitude:",  self._lat_var, "e.g.  40.7128")
        field("Longitude:", self._lng_var, "e.g.  -74.0060")

        # ── Section 5: Templates ──
        section("5 · Templates to Link")
        ttk.Button(inner, text="Fetch Available Templates",
                   command=self._fetch_templates).grid(
            row=row, column=0, columnspan=2, sticky=W, padx=16, pady=(0, 6))
        row += 1

        tmpl_frame = tk.Frame(inner)
        tmpl_frame.grid(row=row, column=0, columnspan=3,
                        sticky=W+E, padx=16, pady=4)
        row += 1
        self._tmpl_list = tk.Listbox(tmpl_frame, selectmode=EXTENDED,
                                     font=FONT_ENTRY, height=6, width=56,
                                     exportselection=False)
        tsb = ttk.Scrollbar(tmpl_frame, orient="vertical",
                             command=self._tmpl_list.yview)
        self._tmpl_list.configure(yscrollcommand=tsb.set)
        self._tmpl_list.pack(side=LEFT, fill=BOTH, expand=True)
        tsb.pack(side=LEFT, fill=Y)
        tk.Label(inner, text="(Ctrl / ⌘ + click to multi-select)",
                 font=FONT_SMALL, fg="#888").grid(
            row=row, column=0, columnspan=3, sticky=W, padx=16)
        row += 1

        ttk.Button(inner, text="▶  Run Full Onboarding",
                   command=self._run_onboarding).grid(
            row=row, column=0, columnspan=3, pady=20)
        row += 1
        inner.columnconfigure(1, weight=1)

    # ── Hosts tab ─────────────────────────────────────────────────────────

    def _build_hosts_tab(self):
        f = self._tab_hosts

        # Search
        sf = ttk.LabelFrame(f, text="  Search Hosts", padding=8)
        sf.pack(fill=X, padx=8, pady=(8, 4))

        tk.Label(sf, text="Name / IP:", font=FONT_LABEL).grid(
            row=0, column=0, sticky=E, padx=(0, 6))
        self._host_search_var = StringVar()
        ttk.Entry(sf, textvariable=self._host_search_var,
                  font=FONT_ENTRY, width=26).grid(row=0, column=1, sticky=W)

        tk.Label(sf, text="Group:", font=FONT_LABEL).grid(
            row=0, column=2, sticky=E, padx=(16, 6))
        self._host_group_filter_var = StringVar()
        self._host_group_filter_cb  = ttk.Combobox(
            sf, textvariable=self._host_group_filter_var,
            font=FONT_ENTRY, width=28, state="readonly")
        self._host_group_filter_cb.grid(row=0, column=3, sticky=W)

        br = tk.Frame(sf)
        br.grid(row=1, column=0, columnspan=4, pady=(8, 0), sticky=W)
        ttk.Button(br, text="🔍 Search",
                   command=self._search_hosts).pack(side=LEFT, padx=(0, 8))
        ttk.Button(br, text="↻ Load Groups",
                   command=self._load_host_groups_filter).pack(side=LEFT, padx=(0, 8))
        ttk.Button(br, text="Clear",
                   command=self._clear_host_search).pack(side=LEFT)
        self._host_count_lbl = tk.Label(br, text="",
                                        font=FONT_SMALL, fg="#888")
        self._host_count_lbl.pack(side=LEFT, padx=16)

        # Treeview
        tf = ttk.LabelFrame(
            f, text="  Results  (Ctrl / ⌘ + click to multi-select)", padding=4)
        tf.pack(fill=BOTH, expand=True, padx=8, pady=4)

        cols = ("hostname", "display_name", "ip", "groups", "proxy")
        self._host_tree = ttk.Treeview(tf, columns=cols, show="headings",
                                        selectmode="extended", height=10)
        widths = {"hostname": 155, "display_name": 155, "ip": 110,
                  "groups": 225, "proxy": 130}
        heads  = {"hostname": "Hostname", "display_name": "Display Name",
                  "ip": "IP Address", "groups": "Current Groups", "proxy": "Proxy"}
        for c in cols:
            self._host_tree.heading(c, text=heads[c],
                                    command=lambda _c=c: self._sort_tree(_c))
            self._host_tree.column(c, width=widths[c], minwidth=60)

        tv_vsb = ttk.Scrollbar(tf, orient="vertical",
                               command=self._host_tree.yview)
        tv_hsb = ttk.Scrollbar(tf, orient="horizontal",
                               command=self._host_tree.xview)
        self._host_tree.configure(yscrollcommand=tv_vsb.set,
                                   xscrollcommand=tv_hsb.set)
        self._host_tree.grid(row=0, column=0, sticky=N+S+E+W)
        tv_vsb.grid(row=0, column=1, sticky=N+S)
        tv_hsb.grid(row=1, column=0, sticky=E+W)
        tf.columnconfigure(0, weight=1)
        tf.rowconfigure(0, weight=1)

        sel_row = tk.Frame(tf)
        sel_row.grid(row=2, column=0, columnspan=2, sticky=W, pady=(4, 0))
        ttk.Button(sel_row, text="Select All",
                   command=self._select_all_hosts).pack(side=LEFT, padx=4)
        ttk.Button(sel_row, text="Deselect All",
                   command=self._deselect_all_hosts).pack(side=LEFT, padx=4)
        self._host_sel_lbl = tk.Label(sel_row, text="0 selected",
                                      font=FONT_SMALL, fg="#888")
        self._host_sel_lbl.pack(side=LEFT, padx=12)
        self._host_tree.bind("<<TreeviewSelect>>",
                              lambda e: self._update_sel_count())

        # Mass update actions
        af = ttk.LabelFrame(f, text="  Actions for Selected Hosts", padding=8)
        af.pack(fill=X, padx=8, pady=(4, 8))

        tk.Label(af, text="Add to Host Group:",
                 font=FONT_LABEL, anchor=E).grid(
            row=0, column=0, sticky=E, padx=(0, 6), pady=5)
        self._mu_group_var = StringVar()
        self._mu_group_cb  = ttk.Combobox(af, textvariable=self._mu_group_var,
                                           font=FONT_ENTRY, width=36,
                                           state="readonly")
        self._mu_group_cb.grid(row=0, column=1, sticky=W, pady=5)
        ttk.Button(af, text="↻ Load",
                   command=self._load_mu_groups).grid(
            row=0, column=2, sticky=W, padx=6, pady=5)

        tk.Label(af, text="Assign Proxy:",
                 font=FONT_LABEL, anchor=E).grid(
            row=1, column=0, sticky=E, padx=(0, 6), pady=5)
        self._mu_proxy_var = StringVar()
        self._mu_proxy_cb  = ttk.Combobox(af, textvariable=self._mu_proxy_var,
                                           font=FONT_ENTRY, width=36,
                                           state="readonly")
        self._mu_proxy_cb.grid(row=1, column=1, sticky=W, pady=5)
        ttk.Button(af, text="↻ Load",
                   command=self._load_mu_proxies).grid(
            row=1, column=2, sticky=W, padx=6, pady=5)

        tk.Label(af, text="Location:",
                 font=FONT_LABEL, anchor=E).grid(
            row=2, column=0, sticky=E, padx=(0, 6), pady=5)
        loc = tk.Frame(af)
        loc.grid(row=2, column=1, sticky=W, pady=5)
        self._mu_lat_var = StringVar()
        self._mu_lng_var = StringVar()
        tk.Label(loc, text="Lat:", font=FONT_SMALL).pack(side=LEFT)
        ttk.Entry(loc, textvariable=self._mu_lat_var,
                  font=FONT_ENTRY, width=12).pack(side=LEFT, padx=(2, 10))
        tk.Label(loc, text="Lon:", font=FONT_SMALL).pack(side=LEFT)
        ttk.Entry(loc, textvariable=self._mu_lng_var,
                  font=FONT_ENTRY, width=12).pack(side=LEFT, padx=(2, 0))
        tk.Label(af, text="(leave blank to skip)",
                 font=FONT_SMALL, fg="#888").grid(
            row=2, column=2, sticky=W, padx=6)

        ttk.Button(af, text="▶  Apply Mass Update to Selected Hosts",
                   command=self._apply_mass_update).grid(
            row=3, column=0, columnspan=3, pady=12)
        af.columnconfigure(1, weight=1)

    # ── PSK Config tab ────────────────────────────────────────────────────

    def _build_psk_tab(self):
        f = self._tab_psk
        tk.Label(f, text="Post-Installation: Configure PSK Encryption",
                 font=FONT_HEAD).grid(row=0, column=0, columnspan=3,
                                      sticky=W, padx=16, pady=(16, 8))

        tk.Label(f, text="Proxy:", font=FONT_LABEL, anchor=E).grid(
            row=1, column=0, sticky=E, padx=(16, 6), pady=8)
        self._psk_proxy_var = StringVar()
        self._psk_proxy_cb  = ttk.Combobox(f, textvariable=self._psk_proxy_var,
                                            font=FONT_ENTRY, width=38,
                                            state="readonly")
        self._psk_proxy_cb.grid(row=1, column=1, sticky=W, pady=8)
        ttk.Button(f, text="↻ Refresh",
                   command=self._refresh_proxies).grid(
            row=1, column=2, sticky=W, padx=6, pady=8)

        tk.Label(f, text="PSK Identity:", font=FONT_LABEL, anchor=E).grid(
            row=2, column=0, sticky=E, padx=(16, 6), pady=8)
        self._psk_identity_var = StringVar()
        ttk.Entry(f, textvariable=self._psk_identity_var,
                  font=FONT_ENTRY, width=42).grid(
            row=2, column=1, columnspan=2, sticky=W, pady=8)

        tk.Label(f, text="PSK (hex):", font=FONT_LABEL, anchor=E).grid(
            row=3, column=0, sticky=E, padx=(16, 6), pady=8)
        self._psk_var = StringVar()
        ttk.Entry(f, textvariable=self._psk_var,
                  font=FONT_ENTRY, width=42).grid(
            row=3, column=1, columnspan=2, sticky=W, pady=8)

        ttk.Separator(f, orient="horizontal").grid(
            row=4, column=0, columnspan=3, sticky=W+E, padx=16, pady=12)
        tk.Label(f, text="—  or import from EDAO Control Hub TXT file  —",
                 font=FONT_SMALL, fg="#888").grid(row=5, column=0, columnspan=3)
        ttk.Button(f, text="📂  Browse TXT File…",
                   command=self._import_txt).grid(
            row=6, column=0, columnspan=3, pady=10)
        self._txt_file_lbl = tk.Label(f, text="No file selected.",
                                      font=FONT_SMALL, fg="#888")
        self._txt_file_lbl.grid(row=7, column=0, columnspan=3)

        ttk.Separator(f, orient="horizontal").grid(
            row=8, column=0, columnspan=3, sticky=W+E, padx=16, pady=12)
        ttk.Button(f, text="🔐  Apply PSK Encryption",
                   command=self._apply_psk).grid(
            row=9, column=0, columnspan=3, pady=8)
        f.columnconfigure(1, weight=1)

    # ── Shared helpers ────────────────────────────────────────────────────

    def _log(self, msg: str, level: str = "INFO"):
        tag = level if level in ("INFO", "OK", "WARN", "ERR") else "INFO"
        self._log_box.configure(state="normal")
        self._log_box.insert(END, msg + "\n", tag)
        self._log_box.configure(state="disabled")
        self._log_box.see(END)

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", END)
        self._log_box.configure(state="disabled")

    def _set_connected(self, connected: bool, info: str = ""):
        self._connected = connected
        if connected:
            self._status_lbl.configure(text="● Connected", fg="#4ec9b0")
            self._api_info_lbl.configure(text=info)
        else:
            self._status_lbl.configure(text="● Not connected", fg="#FF6B6B")
            self._api_info_lbl.configure(text="Not connected.")

    def _autofill_msp_group(self, *_):
        msp = self._msp_var.get().strip()
        # Only auto-fill if the field is blank or matches old auto-value
        current = self._msp_group_var.get().strip()
        if not current or re.match(r'^.+-Group$', current):
            self._msp_group_var.set(f"{msp}-Group" if msp else "")

    def _update_preview(self):
        msp      = self._msp_var.get().strip()
        msp_grp  = self._msp_group_var.get().strip()
        cust     = self._customer_var.get().strip()
        site     = self._site_var.get().strip()
        if msp or cust or site:
            lines = [
                f"Proxy name  :  Proxy{msp}{cust}-{site}",
                f"Group 1     :  MSP/{msp_grp}/{cust}",
                f"Group 2     :  MSP/{msp_grp}/{cust}/{site}",
                f"Disc. rule  :  Proxy-{cust}-{site}",
                f"Disc. action:  Discovery{cust}-{site}",
            ]
            self._preview_var.set("\n".join(lines))
        else:
            self._preview_var.set("—")

    def _toggle_snmp(self):
        self._snmp_entry.configure(
            state="normal" if self._use_snmp.get() else "disabled")

    # ── Connection callbacks ──────────────────────────────────────────────

    def _do_connect(self):
        url  = self._url_var.get().strip()
        mode = self._auth_mode.get()
        if not url:
            messagebox.showwarning("Missing", "Please enter the server URL.")
            return

        def _worker():
            try:
                api = ZabbixAPI(url)
                # apiinfo.version must be called WITHOUT auth header — always first
                ver = api.api_version()
                if mode == "token":
                    tok = self._token_var.get().strip()
                    if not tok:
                        self.after(0, lambda: messagebox.showwarning(
                            "Missing", "Please enter an API token."))
                        return
                    api.use_token(tok)
                    # Verify token works with a privileged read call
                    api.call("hostgroup.get", output=["groupid"], limit=1)
                    info = f"Server : {url}\nAPI ver: {ver}\nAuth   : API Token"
                else:
                    user = self._user_var.get().strip()
                    pwd  = self._pwd_var.get()
                    if not user or not pwd:
                        self.after(0, lambda: messagebox.showwarning(
                            "Missing", "Enter username and password."))
                        return
                    api.login(user, pwd)
                    info = f"Server : {url}\nAPI ver: {ver}\nUser   : {user}"

                self.api = api
                self.after(0, lambda: self._set_connected(True, info))
                self.after(0, lambda: self._log(
                    f"Connected to {url}  (Zabbix {ver})", "OK"))
                self._save_config()
            except Exception as e:
                self.after(0, lambda: self._set_connected(False))
                self.after(0, lambda: self._log(f"Connection failed: {e}", "ERR"))
                self.after(0, lambda: messagebox.showerror(
                    "Connection failed", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _do_disconnect(self):
        if self.api and self._auth_mode.get() == "userpass":
            self.api.logout()
        self.api = None
        self._set_connected(False)
        self._log("Disconnected.")

    # ── Onboarding callbacks ──────────────────────────────────────────────

    def _fetch_templates(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        def _worker():
            try:
                t = self.api.call("template.get",
                                  output=["templateid", "name"],
                                  sortfield="name")
                self._templates = t
                self.after(0, self._populate_templates)
                self.after(0, lambda: self._log(
                    f"Loaded {len(t)} templates.", "OK"))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Failed to fetch templates: {e}", "ERR"))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_templates(self):
        self._tmpl_list.delete(0, END)
        for t in self._templates:
            self._tmpl_list.insert(END, t["name"])

    def _run_onboarding(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        msp      = self._msp_var.get().strip()
        msp_grp  = self._msp_group_var.get().strip()
        customer = self._customer_var.get().strip()
        site     = self._site_var.get().strip()
        proxy_ip = self._proxy_ip_var.get().strip()
        ip_range = self._ip_range_var.get().strip()
        lat      = self._lat_var.get().strip()
        lng      = self._lng_var.get().strip()
        snmp_c   = self._snmp_comm.get().strip() or "public"

        errors = []
        if not msp:      errors.append("MSP Name")
        if not msp_grp:  errors.append("MSP Group Label")
        if not customer: errors.append("Customer Name")
        if not site:     errors.append("Site Name")
        if not proxy_ip: errors.append("Proxy Public IP")
        if not ip_range: errors.append("IP Range")
        if errors:
            messagebox.showwarning("Missing fields",
                "Please fill in:\n• " + "\n• ".join(errors))
            return

        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", proxy_ip):
            messagebox.showwarning("Invalid IP",
                f"'{proxy_ip}' doesn't look like an IPv4 address.")
            return

        sel_idx      = self._tmpl_list.curselection()
        template_ids = [self._templates[i]["templateid"] for i in sel_idx]

        if not messagebox.askyesno("Confirm Onboarding",
            f"About to create:\n\n"
            f"  Proxy       :  Proxy{msp}{customer}-{site}  ({proxy_ip})\n"
            f"  Group 1     :  MSP/{msp_grp}/{customer}\n"
            f"  Group 2     :  MSP/{msp_grp}/{customer}/{site}\n"
            f"  Disc. rule  :  Proxy-{customer}-{site}  (range: {ip_range})\n"
            f"  Disc. action:  Discovery{customer}-{site}\n"
            f"  Templates   :  {len(template_ids)} selected\n\nProceed?"):
            return

        def _worker():
            try:
                ob = Onboarder(self.api,
                    lambda m, lv="INFO": self.after(0, lambda: self._log(m, lv)))
                r = ob.run(
                    msp=msp, msp_group=msp_grp,
                    customer=customer, site=site,
                    proxy_ip=proxy_ip, ip_range=ip_range,
                    use_icmp=self._use_icmp.get(),
                    use_snmp=self._use_snmp.get(),
                    snmp_community=snmp_c,
                    use_agent=self._use_agent.get(),
                    template_ids=template_ids,
                    latitude=lat, longitude=lng,
                )
                self._onboard_results = r
                self.after(0, lambda: messagebox.showinfo(
                    "Onboarding Complete",
                    f"All steps completed!\n\n"
                    f"Proxy ID        : {r['proxy_id']}\n"
                    f"Group IDs       : {r['gid1']}, {r['gid2']}\n"
                    f"Discovery Rule  : {r['drule_id']}\n"
                    f"Discovery Action: {r['action_id']}\n\n"
                    "Next steps:\n"
                    "1. Use the Hosts tab to assign discovered hosts.\n"
                    "2. After proxy is installed on-site, apply PSK\n"
                    "   encryption via the PSK Config tab.",
                ))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Onboarding failed: {e}", "ERR"))
                self.after(0, lambda: messagebox.showerror(
                    "Onboarding failed", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Hosts tab callbacks ───────────────────────────────────────────────

    def _load_host_groups_filter(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        def _worker():
            try:
                groups = self.api.call("hostgroup.get",
                    output=["groupid", "name"], sortfield="name")
                self._host_groups_all = groups
                names = ["— all groups —"] + [g["name"] for g in groups]
                self.after(0, lambda: self._host_group_filter_cb.configure(
                    values=names))
                self.after(0, lambda: self._host_group_filter_var.set(
                    "— all groups —"))
                self.after(0, lambda: self._log(
                    f"Loaded {len(groups)} host groups.", "OK"))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Failed to load groups: {e}", "ERR"))

        threading.Thread(target=_worker, daemon=True).start()

    def _load_mu_groups(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        def _worker():
            try:
                groups = self.api.call("hostgroup.get",
                    output=["groupid", "name"], sortfield="name")
                self._host_groups_all = groups
                names = [g["name"] for g in groups]
                self.after(0, lambda: self._mu_group_cb.configure(values=names))
                self.after(0, lambda: self._log(
                    f"Loaded {len(groups)} groups.", "OK"))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Failed to load groups: {e}", "ERR"))

        threading.Thread(target=_worker, daemon=True).start()

    def _load_mu_proxies(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        def _worker():
            try:
                proxies = self.api.call("proxy.get",
                    output=["proxyid", "name"], sortfield="name")
                self._proxies_all = proxies
                names = [p["name"] for p in proxies]
                self.after(0, lambda: self._mu_proxy_cb.configure(values=names))
                self.after(0, lambda: self._log(
                    f"Loaded {len(proxies)} proxies.", "OK"))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Failed to load proxies: {e}", "ERR"))

        threading.Thread(target=_worker, daemon=True).start()

    def _search_hosts(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        search_text  = self._host_search_var.get().strip()
        group_filter = self._host_group_filter_var.get()
        group_ids    = None
        if group_filter and group_filter != "— all groups —":
            match = [g for g in self._host_groups_all
                     if g["name"] == group_filter]
            if match:
                group_ids = [match[0]["groupid"]]

        def _worker():
            try:
                params = {
                    "output": ["hostid", "host", "name", "proxyid"],
                    "selectGroups":     ["groupid", "name"],
                    "selectInterfaces": ["ip", "type", "main"],
                    "limit": 500,
                    "sortfield": "host",
                }
                if search_text:
                    params["search"]                = {"host": search_text,
                                                       "name": search_text}
                    params["searchByAny"]           = True
                    params["searchWildcardsEnabled"]= True
                if group_ids:
                    params["groupids"] = group_ids

                hosts = self.api.call("host.get", params)

                # Fetch proxy names in batch
                pids = list({h.get("proxyid") for h in hosts
                             if h.get("proxyid")})
                proxy_names = {}
                if pids:
                    px = self.api.call("proxy.get",
                        proxyids=pids, output=["proxyid", "name"])
                    proxy_names = {p["proxyid"]: p["name"] for p in px}

                self._host_rows = hosts
                self.after(0, lambda: self._populate_host_tree(
                    hosts, proxy_names))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Host search failed: {e}", "ERR"))

        threading.Thread(target=_worker, daemon=True).start()

    def _populate_host_tree(self, hosts: list, proxy_names: dict):
        self._host_tree.delete(*self._host_tree.get_children())
        for h in hosts:
            ifaces = h.get("interfaces") or []
            main   = next((i for i in ifaces if i.get("main") == "1"), None)
            ip     = (main or ifaces[0]).get("ip", "—") if ifaces else "—"
            groups = ", ".join(g["name"] for g in (h.get("groups") or []))
            proxy  = proxy_names.get(h.get("proxyid"), "Server")
            self._host_tree.insert("", END, iid=h["hostid"],
                values=(h["host"], h["name"], ip, groups, proxy))
        n = len(hosts)
        self._host_count_lbl.configure(
            text=f"{n} host{'s' if n != 1 else ''} found")
        self._update_sel_count()

    def _clear_host_search(self):
        self._host_search_var.set("")
        self._host_group_filter_var.set("")
        self._host_tree.delete(*self._host_tree.get_children())
        self._host_count_lbl.configure(text="")
        self._update_sel_count()

    def _select_all_hosts(self):
        self._host_tree.selection_set(self._host_tree.get_children())
        self._update_sel_count()

    def _deselect_all_hosts(self):
        self._host_tree.selection_remove(self._host_tree.get_children())
        self._update_sel_count()

    def _update_sel_count(self):
        n = len(self._host_tree.selection())
        self._host_sel_lbl.configure(text=f"{n} selected")

    def _sort_tree(self, col: str):
        items   = [(self._host_tree.set(k, col), k)
                   for k in self._host_tree.get_children("")]
        reverse = getattr(self, f"_sort_rev_{col}", False)
        items.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for i, (_, k) in enumerate(items):
            self._host_tree.move(k, "", i)
        setattr(self, f"_sort_rev_{col}", not reverse)

    def _apply_mass_update(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        selected_ids = list(self._host_tree.selection())
        if not selected_ids:
            messagebox.showwarning("No selection",
                "Please select at least one host.")
            return

        group_name = self._mu_group_var.get().strip()
        proxy_name = self._mu_proxy_var.get().strip()
        lat        = self._mu_lat_var.get().strip()
        lng        = self._mu_lng_var.get().strip()

        if not group_name and not proxy_name and not (lat and lng):
            messagebox.showwarning("Nothing to update",
                "Choose at least one action: group, proxy, or location.")
            return

        group_id = None
        if group_name:
            m = [g for g in self._host_groups_all if g["name"] == group_name]
            if not m:
                messagebox.showerror("Not found",
                    f"Group '{group_name}' not found — click ↻ Load.")
                return
            group_id = m[0]["groupid"]

        proxy_id = None
        if proxy_name:
            m = [p for p in self._proxies_all if p["name"] == proxy_name]
            if not m:
                messagebox.showerror("Not found",
                    f"Proxy '{proxy_name}' not found — click ↻ Load.")
                return
            proxy_id = m[0]["proxyid"]

        parts = []
        if group_name:  parts.append(f"add to '{group_name}'")
        if proxy_name:  parts.append(f"proxy → '{proxy_name}'")
        if lat and lng: parts.append(f"location ({lat}, {lng})")

        if not messagebox.askyesno("Confirm",
            f"Apply to {len(selected_ids)} host(s):\n\n• "
            + "\n• ".join(parts) + "\n\nProceed?"):
            return

        def _worker():
            try:
                ob = Onboarder(self.api,
                    lambda m, lv="INFO": self.after(0, lambda: self._log(m, lv)))
                ob.mass_update_hosts(selected_ids, group_id,
                                     proxy_id, lat, lng)
                self.after(500, self._search_hosts)   # refresh table
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Mass update failed: {e}", "ERR"))
                self.after(0, lambda: messagebox.showerror(
                    "Mass update failed", str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    # ── PSK Config callbacks ──────────────────────────────────────────────

    def _refresh_proxies(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return

        def _worker():
            try:
                proxies = self.api.call("proxy.get",
                    output=["proxyid", "name"], sortfield="name")
                names = [p["name"] for p in proxies]
                self._proxy_map = {p["name"]: p["proxyid"] for p in proxies}
                self.after(0, lambda: self._psk_proxy_cb.configure(values=names))
                self.after(0, lambda: self._log(
                    f"Loaded {len(proxies)} proxies.", "OK"))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"Failed to fetch proxies: {e}", "ERR"))

        self._proxy_map = {}
        threading.Thread(target=_worker, daemon=True).start()

    def _import_txt(self):
        path = filedialog.askopenfilename(
            title="Select EDAO Control Hub TXT file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            content = open(path, encoding="utf-8", errors="replace").read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read file: {e}")
            return

        id_m  = re.search(r"TLSPSKIdentity\s*=\s*(\S+)", content, re.I)
        hex_m = re.search(r"(?:PSK|psk)[:\s=]+([0-9a-fA-F]{32,})", content)

        if id_m:  self._psk_identity_var.set(id_m.group(1))
        if hex_m: self._psk_var.set(hex_m.group(1))

        fname = os.path.basename(path)
        self._txt_file_lbl.configure(text=f"Loaded: {fname}", fg="#4ec9b0")
        if not id_m and not hex_m:
            messagebox.showinfo("Partial parse",
                "Could not auto-detect PSK Identity or PSK hex.\n"
                "Please enter them manually.")
        else:
            self._log(f"Imported PSK data from: {fname}", "OK")

    def _apply_psk(self):
        if not self._connected or not self.api:
            messagebox.showwarning("Not connected", "Please connect first.")
            return
        proxy_name = self._psk_proxy_var.get().strip()
        identity   = self._psk_identity_var.get().strip()
        psk        = self._psk_var.get().strip()
        if not proxy_name:
            messagebox.showwarning("Missing", "Please select a proxy.")
            return
        if not identity or not psk:
            messagebox.showwarning("Missing",
                "PSK Identity and PSK are both required.")
            return
        if not re.fullmatch(r"[0-9a-fA-F]+", psk):
            messagebox.showwarning("Invalid PSK",
                "PSK must be a hexadecimal string.")
            return
        proxy_id = getattr(self, "_proxy_map", {}).get(proxy_name)
        if not proxy_id:
            messagebox.showerror("Error",
                f"Proxy ID not found for '{proxy_name}'. Try refreshing.")
            return

        def _worker():
            try:
                ob = Onboarder(self.api,
                    lambda m, lv="INFO": self.after(0, lambda: self._log(m, lv)))
                ob.configure_psk(proxy_id, identity, psk)
                self.after(0, lambda: messagebox.showinfo(
                    "PSK Applied",
                    f"PSK encryption configured for '{proxy_name}'."))
            except Exception as e:
                self.after(0, lambda: self._log(
                    f"PSK config failed: {e}", "ERR"))
                self.after(0, lambda: messagebox.showerror(
                    "PSK failed", str(e)))

        threading.Thread(target=_worker, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
