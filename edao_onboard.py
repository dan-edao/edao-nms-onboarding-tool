#!/usr/bin/env python3
"""
EDAO-NMS Onboarding Tool v1.2
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

# ── EDAO Logo (embedded PNG, base64) ─────────────────────────────────────────
LOGO_B64 = "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"

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

FONT_LABEL  = ("Helvetica", 14)
FONT_ENTRY  = ("Helvetica", 14)
FONT_LOG    = ("Courier",   13)
FONT_HEAD   = ("Helvetica", 16, "bold")
FONT_SMALL  = ("Helvetica", 12)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EDAO-NMS Onboarding Tool  v1.1")
        self.resizable(True, True)
        self.minsize(900, 760)

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
        # Logo
        try:
            self._logo_img = tk.PhotoImage(data=LOGO_B64)
            logo_lbl = tk.Label(banner, image=self._logo_img,
                                bg="#003366", padx=8, pady=4)
            logo_lbl.pack(side=LEFT)
        except Exception:
            pass
        tk.Label(banner, text="NMS  Onboarding Tool",
                 bg="#003366", fg="white",
                 font=("Helvetica", 20, "bold"), pady=10).pack(side=LEFT, padx=(4,0))
        self._status_lbl = tk.Label(banner, text="● Not connected",
                                    bg="#003366", fg="#FF6B6B",
                                    font=("Helvetica", 13))
        self._status_lbl.pack(side=RIGHT, padx=16)

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
