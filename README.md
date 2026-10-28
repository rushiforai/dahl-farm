# 🚀 Dahl Global API Auto-Farm

A high-speed intelligent automation tool for mass-generating and managing free API keys from **[Dahl Global](https://dahl.global)**, equipped with smart proxy filtering, Tor pool rotation, and automatic integration with **9Router**.

---

> [!IMPORTANT]
> **A Proxy Is Required to Avoid Disrupting the Farm Process (Anti Rate-Limit 429)**
> The Dahl Global server limits account registration per IP address (*HTTP 429 Too Many Requests*). Therefore, **using a proxy (HTTP / SOCKS5) is strongly required** so the farming process runs smoothly, quickly, and without cooldown delays or IP restrictions.
>
> 💡 *Do you not have your own proxy?* You do not need to search for or buy one manually! This repository includes a built-in **Auto-Scraper & Proxy Health Checker** (`filter_proxies.py` or Menu `[2]` in `run.bat`) that automatically finds and validates active public proxies for free.

---

## ✨ Main Features

- 🤖 **Auto-Signup & Provisioning**: Automatically creates random usernames, registers accounts, allocates free token balances (*free token grant*) to new API keys, and verifies inference eligibility.
- 🎲 **Gacha Proxy Farm**: Randomly selects a healthy proxy from the verified list to avoid IP restrictions (*HTTP 429 Rate Limit*).
- 🔍 **Built-in Proxy Checker & Scraper**: Auto-scrapes from multiple public sources and performs real-time parallel latency checks.
- 🧅 **Multi-Instance Tor Pool**: Supports creating a local Tor cluster for automatic identity rotation without limits.
- 🔌 **Auto-Inject to 9Router**: Automatically inserts successfully farmed API keys directly into the SQLite database of [9Router](https://github.com/9router) without manual copy-paste.
- 📁 **Structured Credential Management**: Stores account data (username, user ID, login fingerprint, API key) in a neat local folder.

---

## 📋 System Requirements

1. **Python 3.8 or newer**.
2. **Internet connection**.
3. **Proxy (HTTP / SOCKS5)**: Required for IP rotation so farming is not blocked by limits (can also be generated automatically via the built-in scraper).
4. *(Optional)* **9Router** app if you want to use the auto-inject feature.
5. *(Optional)* **Tor binary** if you want to use Tor pool farming mode.

---

## 🛠️ Installation Guide

1. **Clone this repository:**
   ```bash
   git clone https://github.com/zidnifarchanramadhan-lang/dahl-farm.git
   cd dahl-farm
   ```

2. **Install the required Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 📖 Full Usage Tutorial

There are two easy ways to run this automation:

### Option 1: Use the Windows Interactive Menu (Easiest)

Simply double-click the **`run.bat`** file (or type `run.bat` in Command Prompt / PowerShell):

```
============================================================
     DAHL GLOBAL FARM (ALWAYS USE PROXY)
============================================================

 [1] Farm Accounts (Requires Proxy - Anti 429 and Auto 9Router)
 [2] Filter / Find New Active Proxy (filter_proxies.bat)
 [3] Re-Inject All Saved Keys into 9Router
 [4] View the List of Accounts Already Collected
 [5] Check / Verify API Key Token
 [0] Exit

============================================================
Select menu [1-5, 0]:
```

#### Recommended Flow:
1. **Step 1**: Select **`[2]`** first to find active public proxies that pass Dahl Global validation. The script will check them and save them automatically to `proxies_good.txt`.
2. **Step 2**: Select **`[1]`** to start farming accounts. Enter the number of accounts you want to create (for example: `5` or `10`). The script will rotate proxies and inject successful tokens into 9Router.
3. **Step 3**: Select **`[4]`** to view the summary of accounts and tokens that have already been collected.

---

### Option 2: Run via Command Line (CLI)

You can also run commands directly in the terminal:

#### 1. Filter & Find Active Proxies
Find 20 live proxies ready to use:
```bash
python filter_proxies.py 20
```
> *Note:* If there is no local proxy file yet, the script will automatically download thousands of free proxies from the internet and test them one by one with multi-threading (80 parallel workers).

#### 2. Run the Gacha Proxy Farm (Recommended)
Create 10 accounts with randomized rotation from `proxies_good.txt` and auto-inject to 9Router:
```bash
python dahl_farm.py gachafarm 10
```

If you do not want auto-inject to 9Router, add the `--no-inject` flag:
```bash
python dahl_farm.py gachafarm 10 --no-inject
```

#### 3. Farm Using a Single Proxy or Custom Proxy File
```bash
# Use one specific proxy:
python dahl_farm.py proxyfarm 5 --proxy socks5://127.0.0.1:1080

# Use a custom proxy list file:
python dahl_farm.py proxyfarm 10 --file daftar_proxy_saya.txt
```

#### 4. Sequential Mode (Default, Without Proxy)
```bash
python dahl_farm.py farm 5 --delay 45
```
*(Use a sufficient delay so your internet IP does not get rate-limited)*

#### 5. Inject Saved Tokens into 9Router
To insert all tokens that were previously farmed into 9Router:
```bash
python dahl_farm.py inject9
```

#### 6. Show Accounts and Test API Keys
```bash
# Show all accounts already collected in the creds/ folder
python dahl_farm.py list

# Check whether an API key is still active and responding
python dahl_farm.py check dahl_YOUR_API_KEY_HERE
```

---

## ⚙️ 9Router Integration & Path Configuration

By default, the script automatically detects the local 9Router database in the standard location:
- **Windows**: `%APPDATA%\9router\db\data.sqlite` (`C:\Users\YOUR_USERNAME\AppData\Roaming\9router\db\data.sqlite`)
- **Linux / macOS**: `~/.9router/db/data.sqlite`

### Set a Custom Path (Optional):
If you installed 9Router in a non-standard location, you can set the environment variable:
```bash
# PowerShell:
$env:YOUR_9ROUTER_DB_PATH="D:\custom_path\9router\db\data.sqlite"

# Command Prompt (cmd):
set YOUR_9ROUTER_DB_PATH=D:\custom_path\9router\db\data.sqlite

# Linux/macOS:
export YOUR_9ROUTER_DB_PATH=/path/to/your/9router/db/data.sqlite
```

---

## 📂 Project Directory Structure

```
dahl-farm/
├── dahl_farm.py           # Core automation script for account signup, API allocation, and 9Router injection
├── filter_proxies.py      # Multi-threaded proxy scraper and health checker
├── filter_proxies.bat     # Windows batch shortcut to filter proxies
├── run.bat                # Main interactive console menu (all-in-one CLI UI)
├── farm.bat               # Quick shortcut for running the farming process
├── requirements.txt       # Python dependency list (httpx, socksio)
├── proxies.example.txt    # Example template for supported proxy formats
├── keys.example.txt       # Template for API key storage format
├── .env.example           # Example environment variable configuration
├── .gitignore             # Protects credentials and local cache files
└── creds/                 # (Local) Folder for stored farmed account credentials (not uploaded)
```

---

## 🔒 Security & Privacy Notes

> [!WARNING]
> The `creds/` folder and `keys.txt` file contain your real authentication fingerprints and active API tokens. **Never upload or share the contents of these files publicly.**
> These files are automatically excluded in `.gitignore`.

---

## ⚖️ Disclaimer

This project was created for educational purposes and API interoperability research. Users are fully responsible for using this script in accordance with the relevant service provider's Terms of Service.
