#!/usr/bin/env python3
"""filter_proxies.py - Filter proxy yang aktif, cepat, dan lolos ke inference.dahl.global.

Proxy yang berhasil akan langsung disimpan secara real-time ke 'proxies_good.txt'.
Mendukung input file seperti 'data.txt', 'proxies_all.txt', atau auto-scrape dari internet jika file belum ada.
"""

import os
import sys
import time
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Console encoding UTF-8
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TARGET_URL = 'https://inference.dahl.global/v1/auth/signup'
TIMEOUT = 4.0       # Maksimal respon detik
MAX_WORKERS = 80    # Jumlah thread paralel

GRN, RED, YEL, CYN, DIM, RST = '\033[32m', '\033[31m', '\033[33m', '\033[36m', '\033[2m', '\033[0m'

PUBLIC_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
]


def auto_scrape_proxies():
    """Mengambil proxy publik gratis dari berbagai repositori terpercaya."""
    print(f"  {YEL}[*] Mengunduh proxy publik gratis dari beberapa sumber...{RST}")
    scraped = set()
    for src in PUBLIC_SOURCES:
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                text = resp.read().decode('utf-8', errors='ignore')
                for line in text.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if "://" not in line:
                            # Default prefix
                            if "socks5" in src:
                                line = f"socks5://{line}"
                            else:
                                line = f"http://{line}"
                        scraped.add(line)
        except Exception:
            pass
    print(f"  {GRN}[V] Berhasil mengumpulkan {len(scraped):,} proxy publik gratis!{RST}\n")
    return list(scraped)


def check_proxy(proxy_url):
    """Mengecek apakah proxy hidup, cepat, dan memiliki kuota signup bersih di Dahl."""
    p = proxy_url.strip()
    if not p:
        return None
    if "://" not in p:
        parts = p.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            p = f"http://{user}:{pwd}@{ip}:{port}"
        else:
            p = f"http://{p}"

    t0 = time.time()
    try:
        import httpx
        with httpx.Client(proxy=p, timeout=httpx.Timeout(TIMEOUT, connect=TIMEOUT/2), follow_redirects=False) as c:
            r = c.post(
                TARGET_URL,
                json={"username": ""},
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Content-Type": "application/json",
                    "Origin": "https://inference.dahl.global"
                }
            )
            latency = (time.time() - t0) * 1000
            # Jika 429 = Sudah limit/dipakai orang lain. REJECT!
            if r.status_code == 429:
                return None
            # Jika 400/422 = Domain merespons username invalid -> IP BERSIH & ADA KUOTA!
            if r.status_code in (400, 422, 200, 201):
                return p, latency, r.status_code
    except Exception:
        pass
    return None


def main():
    target_count = 30
    input_file = None

    for arg in sys.argv[1:]:
        if os.path.isfile(arg):
            input_file = Path(arg)
        else:
            try:
                target_count = int(arg)
            except ValueError:
                pass

    here = Path(__file__).resolve().parent
    if not input_file:
        if (here / 'proxies_all.txt').exists():
            input_file = here / 'proxies_all.txt'
        elif (here / 'data.txt').exists():
            input_file = here / 'data.txt'
        elif (here / 'proxies.txt').exists():
            input_file = here / 'proxies.txt'

    output_file = here / 'proxies_good.txt'

    print(f"\n{CYN}======================================================{RST}")
    print(f"{CYN}        PROXY CHECKER & FILTER - DAHL FARM            {RST}")
    print(f"{CYN}======================================================{RST}")
    print(f"  Target Test  : {TARGET_URL}")
    print(f"  Timeout      : {TIMEOUT}s")
    print(f"  Threads      : {MAX_WORKERS}")

    all_proxies = []
    if input_file and input_file.exists():
        print(f"  Input File   : {input_file.name}")
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        print(f"  Input File   : {YEL}Auto-Scrape (Online Sources){RST}")
        all_proxies = auto_scrape_proxies()
        # Simpan raw list ke proxies_all.txt
        raw_file = here / 'proxies_all.txt'
        raw_file.write_text("\n".join(all_proxies), encoding='utf-8')
        print(f"  {DIM}Daftar mentah disimpan ke {raw_file.name}{RST}")

    seen = set()
    deduped = []
    for p in all_proxies:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    all_proxies = deduped

    total = len(all_proxies)
    print(f"  Total Proxy  : {total:,} proxy unik dimuat.")
    print(f"  Output File  : {output_file.name}\n")

    existing_good = set()
    if output_file.exists():
        with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
            existing_good = {line.strip() for line in f if line.strip()}
        print(f"  {DIM}Sudah ada {len(existing_good)} proxy di {output_file.name}{RST}\n")

    print(f"  {YEL}Mencari {target_count} proxy aktif...{RST}")
    print(f"  {DIM}(Tekan Ctrl+C kapan saja untuk berhenti, hasil tersimpan otomatis){RST}\n")

    good_count = 0
    checked_count = 0
    t_start = time.time()

    with open(output_file, 'a', encoding='utf-8') as out_f:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            proxy_iter = iter(all_proxies)
            futures = {}

            for _ in range(min(total, MAX_WORKERS * 3)):
                p = next(proxy_iter, None)
                if p:
                    futures[executor.submit(check_proxy, p)] = p

            try:
                while futures:
                    done_future = next(as_completed(futures))
                    p = futures.pop(done_future)
                    checked_count += 1

                    try:
                        res = done_future.result()
                    except Exception:
                        res = None

                    if res:
                        good_p, latency, status = res
                        if good_p not in existing_good:
                            existing_good.add(good_p)
                            good_count += 1
                            out_f.write(good_p + '\n')
                            out_f.flush()
                            sys.stdout.write(f"\r{' '*80}\r")
                            print(f"  {GRN}V [{good_count:02d}/{target_count}]{RST} {good_p}  {DIM}({latency:.0f}ms, status {status}){RST}")

                            if good_count >= target_count:
                                print(f"\n  {GRN}Target {target_count} proxy aktif tercapai!{RST}")
                                for fut in futures:
                                    fut.cancel()
                                break

                    next_p = next(proxy_iter, None)
                    if next_p:
                        futures[executor.submit(check_proxy, next_p)] = next_p

                    if checked_count % 30 == 0:
                        sys.stdout.write(f"\r  {DIM}Memeriksa: {checked_count:,}/{total:,} | Ditemukan: {good_count} bagus | Waktu: {time.time()-t_start:.1f}s{RST} ")
                        sys.stdout.flush()

            except KeyboardInterrupt:
                print(f"\n\n  {YEL}Dihentikan pengguna. Hasil tersimpan di {output_file.name}.{RST}")

    print(f"\n\n{CYN}======================================================{RST}")
    print(f"  {GRN}Selesai!{RST}")
    print(f"  Proxy baru didapat : {good_count}")
    print(f"  Total di {output_file.name} : {len(existing_good)}")
    print(f"{CYN}======================================================{RST}\n")


if __name__ == '__main__':
    main()
