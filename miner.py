import requests
import time
import json
import threading
import re
import hashlib
import base64
import random

BASE_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

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
# CLASSIFIER (NEW v5 CORE)
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
# SOLVERS
# =========================

def solve(prompt):

    ptype = classify(prompt)
    p = prompt.lower()

    # ---- MATH ----
    if ptype == "math":
        a, op, b = re.findall(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", p)[0]
        a, b = int(a), int(b)
        return str({
            "+": a + b,
            "-": a - b,
            "*": a * b,
            "/": a // b
        }[op])

    # ---- SHA256 ----
    if ptype == "sha256":
        return hashlib.sha256(b"").hexdigest()[:6]

    # ---- ENTROPY ----
    if ptype == "entropy":
        m = re.search(r"(\d+)", p)
        if m:
            return f"2^{m.group(1)}"

    # ---- BASE64 ----
    if ptype == "base64":
        try:
            data = re.findall(r"base64.*?:\s*(.+)", p)[0]
            return base64.b64decode(data).decode().strip()
        except:
            pass

    # ---- HEX ----
    if ptype == "hex":
        try:
            h = re.findall(r"[0-9a-fA-F]{6,}", p)[0]
            return bytes.fromhex(h).decode(errors="ignore").strip()
        except:
            pass

    # ---- REVERSE ----
    if ptype == "reverse":
        return prompt.split(":")[-1].strip()[::-1]

    return None

# =========================
# AI FALLBACK (OPTIONAL)
# =========================

def ai_solve(prompt):
    """
    Optional: local AI via Ollama
    """
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"Solve this puzzle. Return only answer:\n{prompt}",
                "stream": False
            },
            timeout=60
        )
        return r.json()["response"].strip()
    except:
        return "unknown"

# =========================
# MINER LOOP
# =========================

def miner(name, wallet):

    print(f"[START] {name}")

    while True:

        try:
            time.sleep(random.uniform(2, 5))

            r = safe_get(f"{BASE_URL}?eth={wallet}")
            if not r:
                continue

            data = r.json()
            puzzle = data.get("puzzle")

            if not puzzle:
                time.sleep(10)
                continue

            prompt = puzzle["prompt"]
            pid = puzzle["id"]

            print(f"\n[{name}] {prompt}")

            answer = solve(prompt)

            # AI fallback ONLY if needed
            if not answer or answer == "unknown":
                answer = ai_solve(prompt)

            payload = {
                "eth_address": wallet,
                "agent_name": name,
                "puzzle_id": pid,
                "answer": answer
            }

            res = safe_post(payload)

            if res:
                print(f"[{name}] {res.json()}")

        except Exception as e:
            print(f"[{name}] ERROR:", e)
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
    time.sleep(2)

while True:
    time.sleep(999999)
