import requests
import time
import json
import threading
import re
import os

from solvers import SOLVERS

BASE_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# =========================
# MEMORY (v8 improved)
# =========================

MEM_FILE = "memory.json"

if not os.path.exists(MEM_FILE):
    with open(MEM_FILE, "w") as f:
        json.dump({"patterns": {}, "solved": {}}, f)

def load_mem():
    with open(MEM_FILE) as f:
        return json.load(f)

def save_mem(m):
    with open(MEM_FILE, "w") as f:
        json.dump(m, f)

memory = load_mem()

# =========================
# FINGERPRINT ENGINE
# =========================

def fingerprint(text):
    t = text.lower()

    t = re.sub(r"\d+", "X", t)
    t = re.sub(r"[0-9a-f]{6,}", "HEX", t)
    t = re.sub(r"\s+", " ", t)

    return t.strip()

# =========================
# SOLVER ENGINE (v8 CORE)
# =========================

def solve(prompt):

    best = (None, 0.0)

    # memory hit first
    fp = fingerprint(prompt)

    if fp in memory["patterns"]:
        return memory["patterns"][fp]

    # run all solvers
    for solver in SOLVERS:
        try:
            ans, conf = solver(prompt)
            if conf > best[1]:
                best = (ans, conf)
        except:
            pass

    return best[0], best[1]

# =========================
# MINER LOOP
# =========================

def miner(agent, wallet):

    print(f"[START] {agent}")

    while True:

        try:
            time.sleep(2)

            r = requests.get(
                f"{BASE_URL}?eth={wallet}",
                headers=HEADERS,
                timeout=90
            )

            data = r.json()
            puzzle = data.get("puzzle")

            if not puzzle:
                continue

            pid = puzzle["id"]
            prompt = puzzle["prompt"]

            ans, conf = solve(prompt)

            print(f"\n[{agent}] {prompt}")
            print(f"[{agent}] answer={ans} conf={conf}")

            if conf < 0.5:
                ans = "unknown"

            payload = {
                "eth_address": wallet,
                "agent_name": agent,
                "puzzle_id": pid,
                "answer": ans
            }

            res = requests.post(
                BASE_URL,
                headers=HEADERS,
                json=payload,
                timeout=90
            )

            try:
                out = res.json()
                print(f"[{agent}] {out}")

                # learn successful patterns
                if out.get("correct"):
                    memory["patterns"][fp] = ans
                    save_mem(memory)

            except:
                print(res.text)

        except Exception as e:
            print(f"[{agent}] ERROR:", e)
            time.sleep(5)

# =========================
# LOAD WALLETS
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

while True:
    time.sleep(999999)
