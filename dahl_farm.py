#!/usr/bin/env python3
"""
dahl_farm.py — SINGLE FILE: auto-farm for inference.dahl.global API keys.
Combines dahl_farm / farm_fast / tor_pool / farm_pool / sync_keys / export_keys.

Reverse-engineered from the Dahl SPA (accountUi.*.js). Creates new accounts
automatically (without email/password — random fingerprint), fetches API keys,
allocates the free token grant, and tests inference. Results are saved per account in <dir>/creds/.

Zero-dep for the basic mode (stdlib). Tor mode requires `tor` + `httpx`.

Usage:
  python3 dahl_farm.py farm 20 [--delay 45] [--skip-chat]   # sequential, zero-dep
  python3 dahl_farm.py fast 50 [--workers 8] [--pace 5.2]   # parallel, zero-dep
  python3 dahl_farm.py gachafarm 20                         # farm via gacha proxy & auto-inject 9Router
  python3 dahl_farm.py inject9                              # inject all existing API keys into 9Router
  python3 dahl_farm.py proxyfarm 20 [--file proxies.txt]    # farm via HTTP/SOCKS5 proxy
  python3 dahl_farm.py proxyfarm 5 --proxy socks5://...     # farm via a single proxy
  python3 dahl_farm.py torup 6                              # start N tor instances
  python3 dahl_farm.py torfarm 30 [--tor 6] [--pace 5]      # farm via tor pool
  python3 dahl_farm.py tordown                              # stop tor instances
  python3 dahl_farm.py sync                                 # merge keys -> keys.txt
  python3 dahl_farm.py export [--all] [--since YYYY-MM-DD]  # export keys
  python3 dahl_farm.py list                                 # list farmed accounts
  python3 dahl_farm.py check <TOKEN>                        # test a single key

⚠️ DO NOT share the creds/ folder — it contains real account fingerprints & API keys.
"""

import argparse
import json
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, Request, build_opener

# ── configuration ─────────────────────────────────────────────────────
BASE = "https://inference.dahl.global"
HERE = Path(__file__).resolve().parent
CREDS_DIR = HERE / "creds"
MODEL_DEFAULT = "deepseek-ai/DeepSeek-V4-Flash-0731"
POOL_FILE = HERE / "keys.txt"


def _find_tor_bin():
    candidates = [
        HERE / "tor" / "tor" / "tor.exe",
        HERE / "tor" / "tor.exe",
        HERE / "tor.exe",
        Path("/data/data/com.termux/files/usr/bin/tor"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    which = shutil.which("tor") or shutil.which("tor.exe")
    if which:
        return which
    return "/data/data/com.termux/files/usr/bin/tor" if sys.platform != "win32" else str(HERE / "tor" / "tor" / "tor.exe")


TOR_BIN = _find_tor_bin()
TOR_HOME = Path.home() / ".tor_pool"
SOCKS_BASE, CTRL_BASE = 9060, 9160

UA = "Mozilla/5.0 (Android 13; Mobile; rv:156.0) Gecko/156.0 Firefox/156.0"

ADJ = ["swift","quiet","brave","lucky","cosmic","rapid","clever","mellow","crimson",
       "golden","amber","bright","calm","coral","daring","eager","fierce","gentle",
       "icy","jolly","kind","lunar","misty","noble","polar","proud","rusty","silver",
       "solar","tidy","vivid","wild","bold","cozy","keen","nimble"]
NOUN = ["eagle","otter","falcon","panda","comet","signal","raven","tiger","nebula",
        "lynx","badger","birch","bison","cedar","cloud","crane","dove","ember","fern",
        "finch","fox","heron","maple","mink","moose","orca","owl","pebble","pine",
        "robin","seal","spruce","stork","whale","wren","brook"]


def rand_username():
    return f"{random.choice(ADJ)}_{random.choice(NOUN)}_{random.randint(100, 999)}"


def save_cred(rec, idx):
    CREDS_DIR.mkdir(parents=True, exist_ok=True)
    user = rec["user"]["username"]
    f = CREDS_DIR / f"{user}.txt"
    lines = ["# Dahl account credentials",
             "# Keep this file safe: fingerprint = password, cannot be recovered.",
             "# Sign in at: https://dahl.global", "",
             f"username: {user}",
             f"user_id: {rec['user']['user_id']}",
             f"fingerprint: {rec['fingerprint']}",
             f"api_key: {rec['api_key']['token']}",
             f"key_id: {rec['api_key']['id']}",
             f"farmed: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}", ""]
    f.write_text("\n".join(lines))
    return f


# ── sequential client (urllib, zero-dep) ────────────────────────────
class Dahl:
    def __init__(self):
        self.jar = CookieJar()
        self.op = build_opener(HTTPCookieProcessor(self.jar))

    def _req(self, method, path, payload=None, extra=None, timeout=60):
        url = BASE + path
        data = json.dumps(payload).encode() if payload is not None else None
        hdrs = {"User-Agent": UA, "Accept": "application/json",
                "Referer": f"{BASE}/account", "Origin": BASE}
        if data is not None:
            hdrs["Content-Type"] = "application/json"
        if extra:
            hdrs.update(extra)
        req = Request(url, data=data, headers=hdrs, method=method)
        try:
            r = self.op.open(req, timeout=timeout)
            status, raw = r.status, r.read()
        except Exception as e:
            code = getattr(e, "code", None)
            raw = getattr(e, "read", lambda: b"")() if code else b""
            if code:
                status, raw = code, raw
            else:
                raise RuntimeError(f"network error {url}: {e}")
        try:
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {"_raw": raw.decode(errors="replace")}
        return status, body

    def signup(self, u):            return self._req("POST", "/v1/auth/signup", {"username": u})
    def signin(self, fp):           return self._req("POST", "/v1/auth/signin", {"fingerprint": fp})
    def account(self):              return self._req("GET", "/v1/account")
    def allocate(self, kid, amt):   return self._req("POST", "/v1/account/allocate", {"amount": amt, "key_id": kid})
    def signout(self):              return self._req("POST", "/v1/auth/signout")
    def chat(self, model, tok, content="ping"):
        return self._req("POST", "/v1/chat/completions",
                         {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": 4},
                         extra={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})

    def session_cookie(self):
        for c in self.jar:
            if c.name == "dahl_session":
                return c.value
        return None


def do_signup(api, index, tag, backoff=8.0, max_tries=40, reroll_429=False):
    """Sign up with retry/backoff on 429. Returns (body, st)."""
    last = None
    for attempt in range(max_tries):
        st, body = api.signup(rand_username())
        if st in (200, 201):
            return body, st
        if st == 429:
            if reroll_429:
                raise RuntimeError("Proxy IP rate-limited (429)")
            print(f"  [{index:02d}{tag}] 429 -> sleep {backoff:.0f}s", flush=True)
            time.sleep(backoff)
            last = (st, body)
            continue
        raise RuntimeError(f"signup HTTP {st}: {json.dumps(body)[:160]}")
    raise RuntimeError(f"[{index:02d}] signup exhausted retries {last}")

# ── 9Router integration ─────────────────────────────────────────────
def get_9router_db():
    """Locate the local 9Router SQLite database path.

    It can be customized if the user has a non-default path:
    - Environment variable: YOUR_9ROUTER_DB_PATH or ROUTER9_DB_PATH
    - Default Windows: %APPDATA%/9router/db/data.sqlite (C:/Users/YOUR_USERNAME/AppData/Roaming/9router/db/data.sqlite)
    - Default Linux/macOS: ~/.9router/db/data.sqlite
    """
    custom_path = os.environ.get("YOUR_9ROUTER_DB_PATH") or os.environ.get("ROUTER9_DB_PATH")
    if custom_path:
        p = Path(custom_path)
        return p if p.exists() else None

    if sys.platform == "win32":
        p = Path(os.path.expandvars(r"%APPDATA%\9router\db\data.sqlite"))
    else:
        p = Path.home() / ".9router" / "db" / "data.sqlite"
    return p if p.exists() else None


def inject_to_9router(username, token):
    """Insert a Dahl API key into 9Router instantly and automatically."""
    db_path = get_9router_db()
    if not db_path:
        return False, "9Router database not found"
    try:
        import sqlite3, uuid, datetime
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        node_id = "openai-compatible-chat-dahl"

        # Check / create the providerNode for dahl
        cur.execute("SELECT id FROM providerNodes WHERE name='dahl' OR id=?", (node_id,))
        row = cur.fetchone()
        if not row:
            node_data = json.dumps({
                "prefix": "dahl",
                "apiType": "chat",
                "baseUrl": "https://inference.dahl.global/v1"
            })
            cur.execute(
                "INSERT INTO providerNodes (id, type, name, data, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?)",
                (node_id, "openai-compatible", "dahl", node_data, now, now)
            )
        else:
            node_id = row[0]

        # Check whether a connection with this token already exists
        cur.execute("SELECT id FROM providerConnections WHERE data LIKE ?", (f"%{token}%",))
        if cur.fetchone():
            conn.close()
            return True, "already exists"

        conn_id = str(uuid.uuid4())
        conn_data = json.dumps({
            "apiKey": token,
            "baseUrl": "https://inference.dahl.global/v1",
            "testStatus": "active",
            "providerSpecificData": {
                "baseUrl": "https://inference.dahl.global/v1",
                "connectionProxyEnabled": False,
                "connectionProxyUrl": "",
                "connectionNoProxy": ""
            }
        })
        cur.execute(
            "INSERT OR REPLACE INTO providerConnections (id, provider, authType, name, email, priority, isActive, data, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (conn_id, node_id, "apikey", username, None, 1, 1, conn_data, now, now)
        )
        conn.commit()
        conn.close()
        return True, conn_id
    except Exception as e:
        return False, str(e)


def finish_account(api, body, index, tag, model, skip_chat):
    """Signin -> allocate pool -> verify -> save -> auto-inject 9Router."""
    fp, tok, kid = body["fingerprint"], body["api_key"]["token"], body["api_key"]["id"]
    st, _ = api.signin(fp)
    if st != 200:
        raise RuntimeError(f"signin HTTP {st}")
    pool = 0
    st, acc = api.account()
    if st == 200:
        pool = acc.get("token_balance", 0)
    if pool:
        try:
            api.allocate(kid, pool)
        except Exception:
            pass
    if not skip_chat:
        try:
            api.chat(model, tok)
        except Exception:
            pass
    try:
        api.signout()
    except Exception:
        pass
    f = save_cred(body, index)
    user = body["user"]["username"]
    print(f"[{index:02d}{tag}] OK tok={tok[:12]}… pool={pool} SAVED {f.name}", flush=True)

    # Automatically inject directly to 9Router
    try:
        if get_9router_db() is not None:
            inj_ok, conn = inject_to_9router(user, tok)
            if inj_ok and conn != "already exists":
                print(f"  [9Router] ✓ Automatically added to 9Router (Active)", flush=True)
    except Exception:
        pass

    return tok


# ── sub: sequential farm (zero-dep) ────────────────────────────────
def cmd_farm(args):
    ok, fail = [], []
    for i in range(1, args.count + 1):
        try:
            api = Dahl()
            body, st = do_signup(api, i, "[seq]", args.backoff)
            tok = finish_account(api, body, i, "[seq]", args.model, args.skip_chat)
            ok.append(tok)
        except Exception as e:
            print(f"[{i:02d}] FAILED: {e}")
            fail.append(i)
        if i < args.count and args.delay:
            print(f"[--] cooldown {args.delay:.0f}s (rate limit)...")
            time.sleep(args.delay)
    _summary(ok, fail)


# ── sub: parallel farm (zero-dep, adaptive pacing) ──────────────────
# 1 global signup slot; each worker thread runs independently.
_pace_lock = threading.Lock()
_next_ok = 0.0
PACE = 5.2

def paced_signup(api, tag):
    global _next_ok
    while True:
        with _pace_lock:
            now = time.time()
            if now >= _next_ok:
                _next_ok = now + PACE
                break
            wait = _next_ok - now
        time.sleep(min(wait, 1.0))
    return api.signup(tag)

def farm_one_fast(i, model, skip_chat):
    api = Dahl()
    st, body = None, {}
    for _ in range(30):
        st, body = paced_signup(api, rand_username())
        if st in (200, 201):
            break
        if st == 429:
            print(f"[{i:02d}] 429 -> backoff 8s", flush=True)
            time.sleep(8)
            continue
        raise RuntimeError(f"signup HTTP {st}: {json.dumps(body)[:160]}")
    if st not in (200, 201):
        raise RuntimeError(f"[{i:02d}] signup exhausted")
    return finish_account(api, body, i, "[fast]", model, skip_chat)

def cmd_fast(args):
    import concurrent.futures
    global PACE
    PACE = args.pace
    ok = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(farm_one_fast, i, args.model, args.skip_chat)
                for i in range(1, args.count + 1)]
        for f in concurrent.futures.as_completed(futs):
            try:
                ok.append(f.result())
            except Exception as e:
                print(f"[--] worker fail: {e}")
    _summary(ok, [])


# ── sub: tor pool management ───────────────────────────────────────
def _tor_conf(i):
    d = TOR_HOME / f"t{i}"
    d.mkdir(parents=True, exist_ok=True)
    c = d / "torrc"
    data_dir = d.as_posix()
    geoip = (HERE / "tor" / "data" / "geoip").as_posix()
    geoip6 = (HERE / "tor" / "data" / "geoip6").as_posix()
    extra_geo = ""
    if Path(geoip).exists():
        extra_geo = f"GeoIPFile {geoip}\nGeoIPv6File {geoip6}\n"
    c.write_text(
        f"SocksPort 127.0.0.1:{SOCKS_BASE + i}\n"
        f"SocksPolicy accept 127.0.0.1\n"
        f"ControlPort 127.0.0.1:{CTRL_BASE + i}\n"
        f"DataDirectory {data_dir}\nCookieAuthentication 0\n"
        f"{extra_geo}"
        f"Log notice file {data_dir}/tor.log\nPIDFile {data_dir}/tor.pid\n", encoding="utf-8")
    return c

def cmd_torup(args):
    if not Path(TOR_BIN).exists():
        sys.exit(f"tor binary not found: {TOR_BIN} — make sure tor is installed or placed in the tor/ folder")
    n = args.count
    for i in range(n):
        conf = _tor_conf(i)
        pid_file = TOR_HOME / f"t{i}" / "tor.pid"
        if pid_file.exists():
            print(f"[{i}] already running")
            continue
        log = open(TOR_HOME / f"t{i}" / "spawn.log", "a")
        p = subprocess.Popen([TOR_BIN, "-f", str(conf)], stdout=log,
                             stderr=subprocess.STDOUT, start_new_session=True)
        print(f"[{i}] tor PID {p.pid} socks=:{SOCKS_BASE+i} ctrl=:{CTRL_BASE+i}")
    _tor_wait(n)
    _tor_newnym_all(n)
    print("done")

def cmd_tordown(args):
    stopped = 0
    for i in range(32):
        d = TOR_HOME / f"t{i}"
        pid_file = d / "tor.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                if sys.platform == "win32":
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    os.kill(pid, 15)
                stopped += 1
            except Exception:
                pass
            try:
                pid_file.unlink(missing_ok=True)
            except Exception:
                pass
    print(f"Tor pool stopped: {stopped} instances.")

def _tor_wait(n, timeout=90):
    deadline = time.time() + timeout
    ok = 0
    while time.time() < deadline:
        ok = 0
        for i in range(n):
            try:
                s = socket.create_connection(("127.0.0.1", SOCKS_BASE + i), timeout=3)
                s.close(); ok += 1
            except OSError:
                pass
        if ok == n:
            break
        time.sleep(2)
    print(f"boot: {ok}/{n} socks ready")
    return ok

def _tor_newnym(i):
    try:
        s = socket.create_connection(("127.0.0.1", CTRL_BASE + i), timeout=4)
        s.sendall(b'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n')
        r = s.recv(64); s.close()
        return b"250" in r
    except Exception:
        return False

def _tor_newnym_all(n):
    for i in range(n):
        _tor_newnym(i)

def _tor_ip(i):
    try:
        import httpx
        with httpx.Client(proxy=f"socks5://127.0.0.1:{SOCKS_BASE + i}", timeout=20.0) as c:
            return c.get("https://api.ipify.org").text
    except Exception:
        return "?"


# ── sub: farm via tor pool (requires httpx + tor) ─────────────────────
class DahlPool:
    def __init__(self, idx):
        import httpx
        self.c = httpx.Client(proxy=f"socks5://127.0.0.1:{SOCKS_BASE + idx}",
                              timeout=httpx.Timeout(45.0, connect=30.0),
                              follow_redirects=True)

    def _req(self, method, path, payload=None, extra=None, timeout=45):
        hdrs = {"User-Agent": UA, "Accept": "application/json",
                "Referer": f"{BASE}/account", "Origin": BASE}
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        if extra:
            hdrs.update(extra)
        r = self.c.request(method, BASE + path, json=payload, headers=hdrs, timeout=timeout)
        try:
            body = r.json()
        except Exception:
            body = {"_raw": r.text[:200]}
        return r.status_code, body

    def signup(self, u):        return self._req("POST", "/v1/auth/signup", {"username": u})
    def signin(self, fp):       return self._req("POST", "/v1/auth/signin", {"fingerprint": fp})
    def account(self):          return self._req("GET", "/v1/account")
    def allocate(self, kid, a): return self._req("POST", "/v1/account/allocate", {"key_id": kid, "amount": a})
    def signout(self):          return self._req("POST", "/v1/auth/signout", {})
    def chat(self, model, tok):
        return self._req("POST", "/v1/chat/completions",
                         {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 4},
                         extra={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})


_last_signup = {}          # tor idx -> timestamp (per-IP pace)
def _wait_ip_pace(idx, pace):
    last = _last_signup.get(idx, 0.0)
    wait = pace - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_signup[idx] = time.time()

def cmd_torfarm(args):
    try:
        import httpx  # noqa: F401
    except ImportError:
        sys.exit("httpx is missing — install: pip install -r requirements.txt")
    n = args.tor
    print("== check tor pool ==")
    _tor_wait(n, timeout=30)
    for i in range(n):
        print(f"[tor{i}] {_tor_ip(i)}", flush=True)
    print(f"== farm {args.count} via {n} tor instances ==")
    ok, fail = [], []
    for i in range(1, args.count + 1):
        pidx = (i - 1) % n
        _tor_newnym(pidx)
        time.sleep(random.uniform(1.0, 2.5))
        try:
            api = DahlPool(pidx)
            _wait_ip_pace(pidx, args.pace)
            body, st = do_signup(api, i, f"[t{pidx}]", backoff=args.backoff)
            tok = finish_account(api, body, i, f"[t{pidx}]", args.model, args.skip_chat)
            ok.append(tok)
        except Exception as e:
            print(f"[{i:02d}] FAILED: {e}")
            fail.append(i)
    _summary(ok, fail)


# ── sub: farm via HTTP/SOCKS5 proxy pool ───────────────────────────
def _normalize_proxy(p):
    p = p.strip()
    if not p or p.startswith("#"):
        return None
    if "://" not in p:
        parts = p.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            return f"http://{user}:{pwd}@{ip}:{port}"
        return f"http://{p}"
    return p


class DahlProxy:
    def __init__(self, proxy_url=None):
        import httpx
        kwargs = {
            "timeout": httpx.Timeout(45.0, connect=30.0),
            "follow_redirects": True
        }
        if proxy_url:
            kwargs["proxy"] = proxy_url
        self.c = httpx.Client(**kwargs)

    def _req(self, method, path, payload=None, extra=None, timeout=45):
        hdrs = {"User-Agent": UA, "Accept": "application/json",
                "Referer": f"{BASE}/account", "Origin": BASE}
        if payload is not None:
            hdrs["Content-Type"] = "application/json"
        if extra:
            hdrs.update(extra)
        r = self.c.request(method, BASE + path, json=payload, headers=hdrs, timeout=timeout)
        try:
            body = r.json()
        except Exception:
            body = {"_raw": r.text[:200]}
        return r.status_code, body

    def signup(self, u):        return self._req("POST", "/v1/auth/signup", {"username": u})
    def signin(self, fp):       return self._req("POST", "/v1/auth/signin", {"fingerprint": fp})
    def account(self):          return self._req("GET", "/v1/account")
    def allocate(self, kid, a): return self._req("POST", "/v1/account/allocate", {"key_id": kid, "amount": a})
    def signout(self):          return self._req("POST", "/v1/auth/signout", {})
    def chat(self, model, tok):
        return self._req("POST", "/v1/chat/completions",
                         {"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 4},
                         extra={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})


def cmd_proxyfarm(args):
    try:
        import httpx  # noqa: F401
    except ImportError:
        sys.exit("httpx is missing — install: pip install -r requirements.txt")

    proxies = []
    if args.proxy:
        p = _normalize_proxy(args.proxy)
        if p:
            proxies.append(p)
    elif args.file:
        pf = Path(args.file)
        if not pf.exists():
            sys.exit(f"Proxy file not found: {pf}")
        for line in pf.read_text(encoding="utf-8", errors="ignore").splitlines():
            norm = _normalize_proxy(line)
            if norm:
                proxies.append(norm)
    else:
        default_pf = HERE / "proxies.txt"
        if default_pf.exists():
            for line in default_pf.read_text(encoding="utf-8", errors="ignore").splitlines():
                norm = _normalize_proxy(line)
                if norm:
                    proxies.append(norm)

    if not proxies:
        sys.exit("No proxy available! Create a proxies.txt file or use the --proxy <URL> or --file <PATH> option.\nSee the example in proxies.example.txt")

    print(f"== Loaded {len(proxies)} proxies, farming {args.count} accounts ==")
    ok, fail = [], []
    for i in range(1, args.count + 1):
        cur_proxy = proxies[(i - 1) % len(proxies)]
        masked = re.sub(r"://([^:@]+):[^@]+@", r"://\1:***@", cur_proxy)
        print(f"[{i:02d}] Proxy [{masked}]...", flush=True)
        try:
            api = DahlProxy(cur_proxy)
            body, st = do_signup(api, i, f"[pxy{(i-1)%len(proxies)}]", backoff=args.backoff)
            tok = finish_account(api, body, i, f"[pxy{(i-1)%len(proxies)}]", args.model, args.skip_chat)
            ok.append(tok)
        except Exception as e:
            print(f"[{i:02d}] FAILED: {e}")
            fail.append(i)
        if i < args.count and args.delay:
            time.sleep(args.delay)
    _summary(ok, fail)




def cmd_inject9(args):
    """Inject all API keys present in creds/ and keys.txt into 9Router."""
    db_path = get_9router_db()
    if not db_path:
        sys.exit("9Router database not found! Make sure 9Router is installed in %APPDATA%/9router/db/data.sqlite or set YOUR_9ROUTER_DB_PATH.")

    injected, skipped = 0, 0
    PAT_API = re.compile(r"^api_key:\s*(dahl_\w+)", re.M)
    PAT_USER = re.compile(r"^username:\s*(\S+)", re.M)

    items = []
    if CREDS_DIR.exists():
        for f in sorted(CREDS_DIR.glob("*.txt")):
            txt = f.read_text(errors="ignore")
            m_api = PAT_API.search(txt)
            if m_api:
                user = (PAT_USER.search(txt) or [None, f.stem])[1]
                items.append((user, m_api.group(1)))

    if POOL_FILE.exists():
        for line in POOL_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("dahl_"):
                if not any(k == line for _, k in items):
                    items.append((f"user_{line[-6:]}", line))

    print(f"== Found {len(items)} accounts, injecting into 9Router... ==")
    for user, key in items:
        ok, res = inject_to_9router(user, key)
        if ok:
            if res == "already exists":
                skipped += 1
            else:
                injected += 1
                print(f"  [9Router] + Injected: {user} ({key[:16]}...)")
        else:
            print(f"  [9Router] ! Failed: {user} ({res})")

    print(f"\nDone! {injected} accounts were successfully injected into 9Router, {skipped} were already present.")


def load_good_proxies():
    pf = HERE / "proxies_good.txt"
    if pf.exists():
        lines = [line.strip() for line in pf.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#")]
        if lines:
            return lines
    return []


def cmd_gachafarm(args):
    """Farm accounts using the Gacha Proxy system (random from proxies_good.txt) and auto-inject to 9Router."""
    try:
        import httpx
    except ImportError:
        sys.exit("httpx is missing — install: pip install -r requirements.txt")

    good_proxies = load_good_proxies()
    if not good_proxies:
        print("The proxies_good.txt file is missing or empty.")
        print("Running filter_proxies.py automatically to collect active proxies...")
        import subprocess
        subprocess.run([sys.executable, str(HERE / "filter_proxies.py"), str(args.count * 3)])
        good_proxies = load_good_proxies()

    if not good_proxies:
        sys.exit("No active proxies are available in proxies_good.txt! Run: python filter_proxies.py")

    print(f"\n== GACHA PROXY FARM: {args.count} Accounts | Pool: {len(good_proxies)} Active Proxies ==")
    auto_inject = not args.no_inject and get_9router_db() is not None
    if auto_inject:
        print("== Auto-Inject to 9Router Mode: ACTIVE ==")

    ok, fail = [], []
    for i in range(1, args.count + 1):
        gacha_p = random.choice(good_proxies)
        masked = re.sub(r"://([^:@]+):[^@]+@", r"://\1:***@", gacha_p)
        print(f"\n[{i:02d}] Gacha Roll -> {masked}")

        success = False
        for roll in range(30):
            if roll > 0:
                gacha_p = random.choice(good_proxies)
                masked = re.sub(r"://([^:@]+):[^@]+@", r"://\1:***@", gacha_p)
                print(f"[{i:02d}] Reroll Gacha ({roll+1}/30) -> {masked}")
            try:
                api = DahlProxy(gacha_p)
                body, st = do_signup(api, i, "[gacha]", reroll_429=True, max_tries=1)
                tok = finish_account(api, body, i, "[gacha]", args.model, args.skip_chat)
                ok.append(tok)
                success = True
                break
            except Exception as e:
                err_str = str(e)
                if "rate-limited" in err_str or "429" in err_str:
                    print(f"  [Gacha] Proxy limit (429) -> pick another proxy immediately...")
                else:
                    print(f"  [Gacha] Failed ({err_str[:80]}) -> pick another proxy...")

        if not success:
            print(f"[{i:02d}] FAILED after 30 gacha rerolls.")
            fail.append(i)

        if i < args.count and args.delay:
            time.sleep(args.delay)

    _summary(ok, fail)


# ── utils: sync / export / list / check ────────────────────────────
def cmd_sync(args):
    PAT = re.compile(r"^(?:api_key|key)\s*[:=]\s*(dahl_[A-Za-z0-9]+)", re.M)
    keys = {}
    if CREDS_DIR.exists():
        for f in sorted(CREDS_DIR.glob("*.txt")):
            for m in PAT.finditer(f.read_text(errors="ignore")):
                keys[m.group(1)] = f.name
    if POOL_FILE.exists():
        for line in POOL_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("dahl_") and line not in keys:
                keys[line] = "pool-legacy"
    out = "\n".join(sorted(keys)) + "\n"
    POOL_FILE.write_text(out)
    print(f"keys.txt: {len(keys)} unique, {POOL_FILE}")

def cmd_export(args):
    PAT_API = re.compile(r"^api_key:\s*(dahl_\w+)", re.M)
    PAT_USER = re.compile(r"^username:\s*(\S+)", re.M)
    PAT_TIME = re.compile(r"^farmed:\s*(\S+)", re.M)
    since = None if args.all else (args.since or time.strftime("%Y-%m-%d"))
    rows = []
    if CREDS_DIR.exists():
        for f in sorted(CREDS_DIR.glob("*.txt")):
            txt = f.read_text(errors="ignore")
            m_api = PAT_API.search(txt)
            if not m_api:
                continue
            user = (PAT_USER.search(txt) or [None, "?"])[1]
            ts = (PAT_TIME.search(txt) or [None, "?"])[1]
            if since and not ts.startswith(since):
                continue
            rows.append((ts, user, m_api.group(1)))
    rows.sort(key=lambda r: r[0])
    out = Path(args.out) if args.out else HERE / "keys_farmed.txt"
    lines = [f"# Dahl API keys — since {since or 'ALL'}", f"# total: {len(rows)} keys", ""]
    for ts, user, key in rows:
        lines.append(f"{key}   # {user}  {ts}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved: {out}  total: {len(rows)}")
    for ts, user, key in rows:
        print(f"  {key[:18]}…  {user:<20} {ts}")

def cmd_list(args):
    if not CREDS_DIR.exists() or not any(CREDS_DIR.glob("*.txt")):
        print("no creds yet"); return
    for f in sorted(CREDS_DIR.glob("*.txt")):
        d = {}
        for line in f.read_text().splitlines():
            if ": " in line and not line.startswith("#"):
                k, v = line.split(": ", 1); d[k] = v
        print(f"{d.get('username','?'):24s} key={d.get('api_key','?')[:18]}… farmed")

def cmd_check(args):
    api = Dahl()
    st, body = api.chat(args.model, args.token)
    print(f"HTTP {st}")
    print(json.dumps(body, indent=2)[:600])


def _summary(ok, fail):
    print(f"\n=== DONE: {len(ok)} farmed, {len(fail)} failed ===")
    for t in ok:
        print(f"  dahl key: {t}")


def main():
    ap = argparse.ArgumentParser(prog="dahl_farm", description="dahl.global auto-farm — single file")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("farm", help="sequential farm (zero-dep)")
    p.add_argument("count", type=int); p.add_argument("--delay", type=float, default=45)
    p.add_argument("--backoff", type=float, default=8.0)
    p.add_argument("--model", default=MODEL_DEFAULT); p.add_argument("--skip-chat", action="store_true")
    p.set_defaults(fn=cmd_farm)

    p = sub.add_parser("fast", help="parallel farm (zero-dep, adaptive pace)")
    p.add_argument("count", type=int); p.add_argument("--pace", type=float, default=5.2)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--model", default=MODEL_DEFAULT); p.add_argument("--skip-chat", action="store_true")
    p.set_defaults(fn=cmd_fast)

    p = sub.add_parser("torup", help="start N tor instances")
    p.add_argument("count", type=int, nargs="?", default=6)
    p.set_defaults(fn=cmd_torup)

    p = sub.add_parser("tordown", help="stop running tor instances")
    p.set_defaults(fn=cmd_tordown)

    p = sub.add_parser("torfarm", help="farm via tor pool (requires httpx+tor)")
    p.add_argument("count", type=int); p.add_argument("--tor", type=int, default=6)
    p.add_argument("--pace", type=float, default=5.0); p.add_argument("--backoff", type=float, default=8.0)
    p.add_argument("--model", default=MODEL_DEFAULT); p.add_argument("--skip-chat", action="store_true")
    p.set_defaults(fn=cmd_torfarm)

    p = sub.add_parser("proxyfarm", help="farm via HTTP/SOCKS5 proxy pool (requires httpx)")
    p.add_argument("count", type=int)
    p.add_argument("--proxy", help="single proxy url, e.g. http://user:pass@ip:port")
    p.add_argument("--file", help="path to proxies file (default: proxies.txt)")
    p.add_argument("--delay", type=float, default=2.0)
    p.add_argument("--backoff", type=float, default=8.0)
    p.add_argument("--model", default=MODEL_DEFAULT); p.add_argument("--skip-chat", action="store_true")
    p.set_defaults(fn=cmd_proxyfarm)

    p = sub.add_parser("gachafarm", help="farm using random proxies from proxies_good.txt & auto-inject 9Router")
    p.add_argument("count", type=int)
    p.add_argument("--delay", type=float, default=2.0)
    p.add_argument("--backoff", type=float, default=8.0)
    p.add_argument("--no-inject", action="store_true", help="do not auto-inject to 9Router")
    p.add_argument("--model", default=MODEL_DEFAULT); p.add_argument("--skip-chat", action="store_true")
    p.set_defaults(fn=cmd_gachafarm)

    p = sub.add_parser("inject9", help="inject all existing keys into 9Router")
    p.set_defaults(fn=cmd_inject9)

    p = sub.add_parser("sync", help="merge creds -> keys.txt"); p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("export", help="export keys")
    p.add_argument("--all", action="store_true"); p.add_argument("--since", default=None)
    p.add_argument("--out", default=None); p.set_defaults(fn=cmd_export)
    p = sub.add_parser("list", help="list farmed accounts"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("check", help="verify a key")
    p.add_argument("token"); p.add_argument("--model", default=MODEL_DEFAULT); p.set_defaults(fn=cmd_check)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
