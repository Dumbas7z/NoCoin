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
# LOAD MEMORY (LEARNING CORE)
# =========================

MEM_FILE = "memory.json"

if not os.path.exists(MEM_FILE):
    with open(MEM_FILE, "w") as f:
        json.dump({"patterns": {}, "rules_learned": {}}, f)

def load_mem():
    with open(MEM_FILE) as f:
        return json.load(f)

def save_mem(mem):
    with open(MEM_FILE, "w") as f:
        json.dump(mem, f)

memory = load_mem()

# =========================
# SAFE NETWORK
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
# PATTERN LEARNER
# =========================

def learn(prompt, answer, success):

    key = prompt.lower()

    if success:
        memory["patterns"][key] = answer
        save_mem(memory)

# =========================
# SMART CLASSIFIER (v7)
# =========================

def classify(prompt):
    p = prompt.lower()

    # learned patterns first
    if p in memory["patterns"]:
        return "memory"

    if "sha-256" in p:
        return "sha256"

    if re.search(r"\d+\s*bit", p):
        return "entropy"

    if re.search(r"\d+\s*[\+\-\*\/]\s*\d+", p):
        return "math"

    if "base64" in p:
        return "base64"

    if "hex" in p:
        return "hex"

    if "reverse" in p:
        return "reverse"

    return "unknown"

# =========================
# SOLVER ENGINE
# =========================

def solve(prompt):

    p = prompt.lower()
    c = classify(prompt)

    # ---------------- MEMORY HIT ----------------
    if c == "memory":
        return memory["patterns"][p]

    # ---------------- MATH ----------------
    if c == "math":
        a, op, b = re.findall(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", p)[0]
        a, b = int(a), int(b)
        return str({
            "+": a + b,
            "-": a - b,
            "*": a * b,
            "/": a // b
        }[op])

    # ---------------- SHA256 ----------------
    if c == "sha256":
        return hashlib.sha256(b"").hexdigest()[:6]

    # ---------------- ENTROPY LEARNED RULE ----------------
    if c == "entropy":
        m = re.search(r"(\d+)", p)
        if m:
            return f"2^{m.group(1)}"

    # ---------------- BASE64 ----------------
    if c == "base64":
        try:
            data = re.findall(r"base64.*?:\s*(.+)", p)[0]
            return base64.b64decode(data).decode().strip()
        except:
            pass

    # ---------------- HEX ----------------
    if c == "hex":
        try:
            h = re.findall(r"[0-9a-fA-F]{6,}", p)[0]
            return bytes.fromhex(h).decode(errors="ignore").strip()
        except:
            pass

    # ---------------- REVERSE ----------------
    if c == "reverse":
        return prompt.split(":")[-1].strip()[::-1]

    return None

# =========================
# CONFIDENCE SYSTEM
# =========================

def confidence(answer):
    if answer is None:
        return 0.0
    if answer == "unknown":
        return 0.2
    return 0.9

# =========================
# MINER LOOP (SELF-LEARNING)
# =========================

def miner(agent, wallet):

    print(f"[START] {agent}")

    while True:

        try:
            time.sleep(random.uniform(2, 5))

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

            answer = solve(prompt)
            conf = confidence(answer)

            # AI fallback only if low confidence
            if conf < 0.5:
                answer = "unknown"

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
                    print(f"[{agent}] RAW:", res.text)

            # ---------------- LEARNING STEP ----------------
            learn(prompt, answer, success)

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
