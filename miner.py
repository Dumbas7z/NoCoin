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
# SAFE REQUESTS
# =========================

def safe_get(url, headers):
    for _ in range(3):
        try:
            return requests.get(url, headers=headers, timeout=90)
        except:
            time.sleep(2)
    return None


def safe_post(url, headers, payload):
    for _ in range(3):
        try:
            return requests.post(url, headers=headers, json=payload, timeout=90)
        except:
            time.sleep(2)
    return None


# =========================
# CORE SOLVER ENGINE
# =========================

def solve_puzzle(prompt):
    p = prompt.lower().strip()

    # -------------------------
    # 1. BASIC ARITHMETIC
    # -------------------------
    m = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', p)
    if m:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return str({
            "+": a + b,
            "-": a - b,
            "*": a * b,
            "/": a // b
        }[op])

    # -------------------------
    # 2. SHA256 EMPTY STRING
    # -------------------------
    if "sha-256" in p and "empty string" in p:
        return hashlib.sha256(b"").hexdigest()[:6]

    # -------------------------
    # 3. 256-BIT KEYSPACE (SEMANTIC)
    # -------------------------
    if re.search(r"256[- ]bit", p) and "private key" in p:
        return "2^256"

    if "how many possible" in p and "256" in p and "power of 2" in p:
        return "2^256"

    # -------------------------
    # 4. GENERAL ENTROPY QUESTIONS
    # -------------------------
    if "how many possible" in p and "bit" in p:
        bits = re.search(r"(\d+)\s*bit", p)
        if bits:
            n = int(bits.group(1))
            return f"2^{n}"

    # -------------------------
    # 5. BASE64 DECODE
    # -------------------------
    if "base64 decode" in p:
        try:
            match = re.search(r'base64.*?:\s*(.+)', p)
            if match:
                return base64.b64decode(match.group(1)).decode().strip()
        except:
            pass

    # -------------------------
    # 6. HEX DECODE
    # -------------------------
    if "hex" in p and "decode" in p:
        try:
            match = re.findall(r'([0-9a-fA-F]{6,})', p)
            if match:
                return bytes.fromhex(match[0]).decode(errors="ignore").strip()
        except:
            pass

    # -------------------------
    # 7. REVERSE STRING
    # -------------------------
    if "reverse" in p:
        try:
            return prompt.split(":")[-1].strip()[::-1]
        except:
            pass

    # -------------------------
    # 8. FALLBACK (SAFE GUESSING)
    # -------------------------
    return "unknown"


# =========================
# MINER LOOP
# =========================

def miner_loop(agent_name, wallet):

    print(f"[START] {agent_name}")

    while True:

        try:
            time.sleep(random.uniform(2, 5))

            r = safe_get(f"{BASE_URL}?eth={wallet}", HEADERS)

            if not r:
                continue

            data = r.json()
            puzzle = data.get("puzzle")

            if not puzzle:
                time.sleep(10)
                continue

            pid = puzzle["id"]
            prompt = puzzle["prompt"]

            print(f"\n[{agent_name}] PUZZLE:", pid)
            print(f"[{agent_name}] PROMPT:", prompt)

            answer = solve_puzzle(prompt)

            payload = {
                "eth_address": wallet,
                "agent_name": agent_name,
                "puzzle_id": pid,
                "answer": answer
            }

            r2 = safe_post(BASE_URL, HEADERS, payload)

            if r2:
                try:
                    print(f"[{agent_name}] RESULT:", r2.json())
                except:
                    print(f"[{agent_name}] RAW:", r2.text)

        except Exception as e:
            print(f"[{agent_name}] ERROR:", e)
            time.sleep(5)


# =========================
# LOAD WALLETS
# =========================

with open("wallets.json", "r") as f:
    wallets = json.load(f)


# =========================
# START AGENTS
# =========================

for w in wallets:
    t = threading.Thread(
        target=miner_loop,
        args=(w["agent_name"], w["wallet"]),
        daemon=True
    )
    t.start()
    time.sleep(2)


# KEEP ALIVE
while True:
    time.sleep(999999)
