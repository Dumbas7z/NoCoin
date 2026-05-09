import requests
import time
import json
import threading
import re
import hashlib
import base64
import random

BASE_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# =========================
# PERFORMANCE STATE
# =========================

stats = {}

def update_stats(agent, success):
    if agent not in stats:
        stats[agent] = {"ok": 0, "fail": 0}

    if success:
        stats[agent]["ok"] += 1
    else:
        stats[agent]["fail"] += 1

def success_rate(agent):
    s = stats.get(agent, {"ok": 0, "fail": 0})
    total = s["ok"] + s["fail"]
    if total == 0:
        return 1.0
    return s["ok"] / total

# =========================
# SMART BACKOFF (IMPORTANT)
# =========================

def adaptive_delay(agent):
    rate = success_rate(agent)

    if rate < 0.3:
        return 10   # struggling → slow down
    if rate < 0.6:
        return 5
    return random.uniform(1.5, 3)

# =========================
# SOLVERS
# =========================

def solve(prompt):
    p = prompt.lower()

    # math
    m = re.search(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", p)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return str({
            "+": a + b,
            "-": a - b,
            "*": a * b,
            "/": a // b
        }[op]), 0.95

    # sha256 empty string
    if "sha-256" in p and "empty string" in p:
        return hashlib.sha256(b"").hexdigest()[:6], 0.99

    # entropy (bit questions)
    if "bit" in p and "private key" in p:
        m = re.search(r"(\d+)", p)
        if m:
            return f"2^{m.group(1)}", 0.92

    # base64
    if "base64" in p:
        try:
            data = re.findall(r"base64.*?:\s*(.+)", p)[0]
            return base64.b64decode(data).decode().strip(), 0.85
        except:
            return None, 0.0

    # hex
    if "hex" in p:
        try:
            h = re.findall(r"[0-9a-fA-F]{6,}", p)[0]
            return bytes.fromhex(h).decode(errors="ignore").strip(), 0.85
        except:
            return None, 0.0

    # reverse
    if "reverse" in p:
        return prompt.split(":")[-1].strip()[::-1], 0.8

    return None, 0.0

# =========================
# CONFIDENCE FILTER
# =========================

def should_submit(answer, confidence):
    """
    CORE OPTIMIZATION RULE:
    Only submit high-confidence answers
    """
    if answer is None:
        return False
    if confidence < 0.85:
        return False
    if answer == "unknown":
        return False
    return True

# =========================
# NETWORK SAFE CALLS
# =========================

def safe_get(url):
    for _ in range(3):
        try:
            return requests.get(url, headers=HEADERS, timeout=90)
        except:
            time.sleep(2)
    return None

def safe_post(payload):
    for _ in range(3):
        try:
            return requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=90)
        except:
            time.sleep(2)
    return None

# =========================
# MINER LOOP (FINAL VERSION)
# =========================

def miner(agent, wallet):

    print(f"[START] {agent}")

    while True:

        try:
            time.sleep(adaptive_delay(agent))

            r = safe_get(f"{BASE_URL}?eth={wallet}")
            if not r:
                continue

            data = r.json()
            puzzle = data.get("puzzle")

            if not puzzle:
                continue

            pid = puzzle["id"]
            prompt = puzzle["prompt"]

            print(f"\n[{agent}] {prompt}")

            answer, conf = solve(prompt)

            print(f"[{agent}] answer={answer} confidence={conf:.2f}")

            # =========================
            # OPTIMIZATION CORE
            # =========================

            if not should_submit(answer, conf):
                print(f"[{agent}] SKIP (low confidence)")
                continue

            payload = {
                "eth_address": wallet,
                "agent_name": agent,
                "puzzle_id": pid,
                "answer": answer
            }

            res = safe_post(payload)

            success = False

            if res:
                try:
                    out = res.json()
                    success = out.get("correct", False)
                    print(f"[{agent}] {out}")
                except:
                    print(res.text)

            update_stats(agent, success)

        except Exception as e:
            print(f"[{agent}] ERROR:", e)
            time.sleep(5)

# =========================
# LOAD AGENTS
# =========================

with open("wallets.json") as f:
    wallets = json.load(f)

for w in wallets:
    t = threading.Thread(
        target=miner,
        args=(w["agent_name"], w["wallet"]),
        daemon=True
    )
    t.start()
    time.sleep(2)

while True:
    time.sleep(999999)
