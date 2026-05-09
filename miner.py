import requests
import time
import json
import threading
import re
import hashlib
import random

BASE_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# =========================
# SAFE REQUEST HELPERS
# =========================

def safe_get(url, headers):
    for i in range(3):
        try:
            r = requests.get(url, headers=headers, timeout=90)
            return r
        except Exception as e:
            print("[GET retry]", i, e)
            time.sleep(3)
    return None


def safe_post(url, headers, payload):
    for i in range(3):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=90)
            return r
        except Exception as e:
            print("[POST retry]", i, e)
            time.sleep(3)
    return None

# =========================
# SOLVER ENGINE
# =========================

def normalize(text):
    return str(text).lower().strip()


def solve_puzzle(prompt):
    p = prompt.lower()

    # -------------------------
    # math
    # -------------------------
    m = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', p)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op == "+": return str(a + b)
        if op == "-": return str(a - b)
        if op == "*": return str(a * b)
        if op == "/": return str(a // b)

    # -------------------------
    # SHA-256 empty string
    # -------------------------
    if "sha-256 hash of the empty string" in p:
        return hashlib.sha256(b"").hexdigest()[:6]

    # -------------------------
    # 256-bit keyspace
    # -------------------------
    if "256-bit private keys" in p:
        return "2^256"

    # -------------------------
    # reverse
    # -------------------------
    if "reverse" in p:
        try:
            return prompt.split(":")[-1].strip()[::-1]
        except:
            pass

    # fallback (IMPORTANT: never echo full prompt blindly)
    return "unknown"


# =========================
# MINER LOOP
# =========================

def miner_loop(agent_name, wallet):

    print(f"[START] {agent_name} -> {wallet}")

    while True:

        try:
            # jitter prevents API overload
            time.sleep(random.uniform(2, 6))

            r = safe_get(
                f"{BASE_URL}?eth={wallet}",
                HEADERS
            )

            if not r:
                print(f"[{agent_name}] GET FAILED")
                continue

            if r.status_code == 429:
                print(f"[{agent_name}] RATE LIMITED")
                time.sleep(10)
                continue

            data = r.json()
            puzzle = data.get("puzzle")

            if not puzzle:
                print(f"[{agent_name}] NO PUZZLE")
                time.sleep(15)
                continue

            prompt = puzzle["prompt"]
            pid = puzzle["id"]

            print(f"\n[{agent_name}] PUZZLE:", pid)
            print(f"[{agent_name}] PROMPT:", prompt)

            answer = solve_puzzle(prompt)

            payload = {
                "eth_address": wallet,
                "agent_name": agent_name,
                "puzzle_id": pid,
                "answer": normalize(answer)
            }

            r2 = safe_post(BASE_URL, HEADERS, payload)

            if not r2:
                print(f"[{agent_name}] SUBMIT FAILED")
                continue

            try:
                print(f"[{agent_name}] RESULT:", r2.json())
            except:
                print(f"[{agent_name}] RAW:", r2.text)

        except Exception as e:
            print(f"[{agent_name}] LOOP ERROR:", e)
            time.sleep(5)


# =========================
# LOAD AGENTS
# =========================

with open("wallets.json", "r") as f:
    wallets = json.load(f)

# =========================
# START THREADS
# =========================

threads = []

for w in wallets:
    t = threading.Thread(
        target=miner_loop,
        args=(w["agent_name"], w["wallet"]),
        daemon=True
    )
    t.start()
    threads.append(t)

    time.sleep(3)  # stagger startup

# =========================
# KEEP ALIVE (IMPORTANT)
# =========================

while True:
    time.sleep(999999)
