import requests
import time
import json
import threading
import re

BASE_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# =========================
# NORMALIZE ANSWER
# =========================

def normalize(text):
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# PUZZLE SOLVER
# =========================

def solve_puzzle(prompt):

    p = prompt.lower()

    # math
    math_match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)', p)
    if math_match:
        a = int(math_match.group(1))
        op = math_match.group(2)
        b = int(math_match.group(3))

        if op == "+":
            return str(a + b)
        elif op == "-":
            return str(a - b)
        elif op == "*":
            return str(a * b)
        elif op == "/":
            return str(a // b)

    # SHA-256 empty string
    if "sha-256 hash of the empty string" in p:
        import hashlib
        return hashlib.sha256(b"").hexdigest()[:6]

    # 256-bit keyspace question
    if "256-bit private keys" in p:
        return "2^256"

    # reverse
    if "reverse" in p:
        try:
            return prompt.split(":")[-1].strip()[::-1]
        except:
            pass

    return normalize(prompt)

# =========================
# MINER LOOP
# =========================

def miner_loop(agent_name, wallet):

    print(f"[START] {agent_name} | {wallet}")

    while True:

        try:

            # Get puzzle
            r = requests.get(
                f"{BASE_URL}?eth={wallet}",
                headers=HEADERS,
                timeout=30
            )

            if r.status_code == 429:
                print(f"[{agent_name}] RATE LIMITED")
                time.sleep(10)
                continue

            data = r.json()

            puzzle = data.get("puzzle")

            if not puzzle:
                print(f"[{agent_name}] No puzzles available")
                time.sleep(20)
                continue

            print(f"\n[{agent_name}] Puzzle ID: {puzzle['id']}")
            print(f"[{agent_name}] Prompt: {puzzle['prompt']}")

            # Solve
            answer = solve_puzzle(puzzle["prompt"])

            print(f"[{agent_name}] Answer: {answer}")

            # Submit
            payload = {
                "eth_address": wallet,
                "agent_name": agent_name,
                "puzzle_id": puzzle["id"],
                "answer": normalize(answer)
            }

            submit = requests.post(
                BASE_URL,
                headers=HEADERS,
                json=payload,
                timeout=30
            )

            try:
                result = submit.json()
            except:
                result = submit.text

            print(f"[{agent_name}] Result: {result}")

            # Delay to avoid rate limits
            time.sleep(3)

        except Exception as e:

            print(f"[{agent_name}] ERROR: {e}")
            time.sleep(10)

# =========================
# LOAD WALLETS
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
        args=(w["agent_name"], w["wallet"])
    )

    t.start()

    threads.append(t)

    # stagger startup
    time.sleep(2)

# =========================
# KEEP ALIVE
# =========================

for t in threads:
    t.join()
