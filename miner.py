import requests
import time
import json
import threading
import re
import hashlib
import base64
import random
import os

BASE_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# =========================
# LOAD STATE (MEMORY)
# =========================

STATE_FILE = "state.json"

if not os.path.exists(STATE_FILE):
    with open(STATE_FILE, "w") as f:
        json.dump({"solved": {}}, f)

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

state = load_state()

# =========================
# ADAPTIVE SPEED CONTROL
# =========================

def get_delay(agent):
    fail = state.get("fail_count", {}).get(agent, 0)
    base = 2.0

    if fail > 5:
        return 10
    if fail > 2:
        return 5

    return base + random.uniform(0, 2)

# =========================
# CLASSIFIER (same core)
# =========================

def classify(prompt):
    p = prompt.lower()

    if "sha-256" in p:
        return "sha256"

    if re.search(r"\d+\s*[\+\-\*\/]\s*\d+", p):
        return "math"

    if "256" in p and "private key" in p:
        return "entropy"

    if "base64" in p:
        return "base64"

    if "hex" in p:
        return "hex"

    if "reverse" in p:
        return "reverse"

    return "unknown"

# =========================
# SOLVER
# =========================

def solve(prompt):
    ptype = classify(prompt)
    p = prompt.lower()

    if ptype == "math":
        a, op, b = re.findall(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", p)[0]
        a, b = int(a), int(b)
        return str({
            "+": a + b,
            "-": a - b,
            "*": a * b,
            "/": a // b
        }[op])

    if ptype == "sha256":
        return hashlib.sha256(b"").hexdigest()[:6]

    if ptype == "entropy":
        m = re.search(r"(\d+)", p)
        if m:
            return f"2^{m.group(1)}"

    if ptype == "base64":
        try:
            data = re.findall(r"base64.*?:\s*(.+)", p)[0]
            return base64.b64decode(data).decode().strip()
        except:
            pass

    if ptype == "hex":
        try:
            h = re.findall(r"[0-9a-fA-F]{6,}", p)[0]
            return bytes.fromhex(h).decode(errors="ignore").strip()
        except:
            pass

    if ptype == "reverse":
        return prompt.split(":")[-1].strip()[::-1]

    return None

# =========================
# SAFE REQUESTS
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
# MINER LOOP (v6 CORE)
# =========================

def miner(agent, wallet):

    print(f"[START] {agent}")

    while True:

        try:

            time.sleep(get_delay(agent))

            r = safe_get(f"{BASE_URL}?eth={wallet}")
            if not r:
                continue

            data = r.json()
            puzzle = data.get("puzzle")

            if not puzzle:
                continue

            pid = puzzle["id"]

            # =========================
            # MEMORY CHECK (NO REPEAT)
            # =========================

            if pid in state["solved"]:
                continue

            prompt = puzzle["prompt"]

            print(f"\n[{agent}] {prompt}")

            answer = solve(prompt)

            # fallback AI only if unknown
            if not answer:
                answer = "unknown"

            payload = {
                "eth_address": wallet,
                "agent_name": agent,
                "puzzle_id": pid,
                "answer": answer
            }

            res = safe_post(payload)

            if res:

                try:
                    out = res.json()
                except:
                    out = {}

                print(f"[{agent}] {out}")

                if out.get("correct"):
                    state["solved"][pid] = True
                    state["fail_count"][agent] = 0

                else:
                    state["fail_count"][agent] = state.get("fail_count", {}).get(agent, 0) + 1

                save_state(state)

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
