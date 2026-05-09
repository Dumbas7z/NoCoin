import re
import hashlib
import base64

# =========================
# SOLVER REGISTRY
# =========================

def math_solver(p):
    m = re.search(r"(\d+)\s*([\+\-\*\/])\s*(\d+)", p)
    if not m:
        return None, 0.0

    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))

    return str({
        "+": a + b,
        "-": a - b,
        "*": a * b,
        "/": a // b
    }[op]), 0.95


def sha_solver(p):
    if "sha-256" in p and "empty string" in p:
        return hashlib.sha256(b"").hexdigest()[:6], 0.99
    return None, 0.0


def entropy_solver(p):
    if "bit" in p and "private key" in p:
        m = re.search(r"(\d+)", p)
        if m:
            return f"2^{m.group(1)}", 0.9
    return None, 0.0


def base64_solver(p):
    if "base64" not in p:
        return None, 0.0

    try:
        data = re.findall(r"base64.*?:\s*(.+)", p)[0]
        return base64.b64decode(data).decode().strip(), 0.85
    except:
        return None, 0.0


def hex_solver(p):
    if "hex" not in p:
        return None, 0.0

    try:
        h = re.findall(r"[0-9a-fA-F]{6,}", p)[0]
        return bytes.fromhex(h).decode(errors="ignore").strip(), 0.85
    except:
        return None, 0.0


def reverse_solver(p):
    if "reverse" not in p:
        return None, 0.0

    try:
        return p.split(":")[-1].strip()[::-1], 0.8
    except:
        return None, 0.0


# =========================
# REGISTERED SOLVERS
# =========================

SOLVERS = [
    math_solver,
    sha_solver,
    entropy_solver,
    base64_solver,
    hex_solver,
    reverse_solver
]
