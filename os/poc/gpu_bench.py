"""
os.poc.gpu_bench
==================

Proof of concept 1 for MIA OS (DEC-0189, `docs/mia_os/MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md` section 2): how
fast the RX 7900 XTX runs MIA's three models under Linux, against what the same PC measured on Windows on
2026-11-15. Run it in a Fedora live session with Ollama serving (steps in `os/poc/README.md`).

Standard library only, so it runs on a fresh live USB with `python3 os/poc/gpu_bench.py` (or `curl ... | python3`).
For each model it times a cold load and a warm answer through Ollama's own API (the same prompt and settings as the
Windows measurement), asks Ollama whether the model sat on the GPU, unloads it, and prints a table with the Windows
figures beside it, then a verdict against the PoC's bar (the 14B at 65 tokens a second or more). It also writes
everything to `mia_gpu_bench.json` in the current folder. Nothing on the computer is changed.
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:11434"
PROMPT = "In two sentences, what should I check first if my greenhouse fan stopped running?"  # as on Windows
MODELS = ("llama3.2:latest", "qwen3:14b", "qwen2.5:32b")
WINDOWS = {"llama3.2:latest": (4.1, 220.0), "qwen3:14b": (11.2, 73.0), "qwen2.5:32b": (37.0, 14.0)}  # load s, tok/s
BAR = ("qwen3:14b", 65.0)


def _post(path: str, body: dict, timeout: float = 900) -> dict:
    """One call to Ollama's API."""
    req = urllib.request.Request(API + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def _get(path: str) -> dict:
    """One read from Ollama's API."""
    with urllib.request.urlopen(API + path, timeout=30) as r:
        return json.load(r)


def generate(model: str, keep: str) -> dict:
    """A non-streamed answer with the Windows measurement's settings, and its wall time."""
    started = time.perf_counter()
    out = _post("/api/generate", {"model": model, "prompt": PROMPT, "stream": False, "keep_alive": keep,
                                  "options": {"num_predict": 64, "temperature": 0}})
    out["wall"] = time.perf_counter() - started
    return out


def on_gpu(model: str) -> str:
    """How much of the loaded model Ollama put in video memory ("100% GPU", "40% GPU", "CPU")."""
    try:
        for m in _get("/api/ps").get("models", []):
            if m.get("name", "").startswith(model.split(":")[0]):
                vram, size = m.get("size_vram", 0), max(m.get("size", 1), 1)
                return "CPU" if not vram else f"{round(100 * vram / size)}% GPU"
    except (urllib.error.URLError, OSError):
        pass
    return "unknown"


def measure(model: str) -> dict:
    """Cold load and warm writing speed for one model, then unloads it."""
    ns = 1e9
    try:
        cold = generate(model, "5m")
        where = on_gpu(model)
        warm = generate(model, "0s")
    except urllib.error.HTTPError as problem:
        return {"model": model, "error": f"{problem.code}: {problem.read().decode(errors='replace')[:200]}"}
    except (urllib.error.URLError, OSError) as problem:
        return {"model": model, "error": str(problem)[:200]}
    return {"model": model, "where": where,
            "cold_load_s": round(cold.get("load_duration", 0) / ns, 1),
            "warm_first_token_s": round((warm.get("load_duration", 0) + warm.get("prompt_eval_duration", 0)) / ns, 2),
            "write_tok_s": round(warm.get("eval_count", 0) / max(warm.get("eval_duration", 1) / ns, 1e-9), 1)}


def _run(cmd: list[str]) -> str:
    """A command's first lines of output, or why it couldn't run (for the hardware notes)."""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip()[:600]
    except (OSError, subprocess.TimeoutExpired) as problem:
        return f"(couldn't run: {problem})"


def hardware() -> dict:
    """What the live session sees of the PC: the GPU, ROCm's view of it, Wi-Fi, Bluetooth, the TPM, the kernel."""
    tpm = _run(["cat", "/sys/class/tpm/tpm0/tpm_version_major"])
    return {"kernel": platform.release(), "gpu": _run(["sh", "-c", "lspci | grep -iE 'vga|3d|display'"]),
            "rocm_agents": _run(["sh", "-c", "rocminfo 2>/dev/null | grep -E 'Marketing Name|gfx' | head -6"]),
            "network": _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"]),
            "bluetooth": _run(["sh", "-c", "bluetoothctl list 2>&1 | head -3"]),
            "tpm_version": tpm, "ollama": _run(["ollama", "--version"])}


def main() -> int:
    """Measures every model that's present, prints the comparison and the verdict; 0 when the bar is met."""
    try:
        have = {m["name"] for m in _get("/api/tags").get("models", [])}
    except (urllib.error.URLError, OSError):
        print("Ollama isn't answering on 127.0.0.1:11434. Start it (see os/poc/README.md) and run this again.")
        return 2
    models = [m for m in (sys.argv[1:] or MODELS) if m in have]
    missing = [m for m in (sys.argv[1:] or MODELS) if m not in have]
    results = [measure(m) for m in models]
    print(f"\n{'Model':18} {'On':10} {'Load s':>7} {'(Win)':>6} {'Writes tok/s':>13} {'(Win)':>6}")
    for r in results:
        win_load, win_tok = WINDOWS.get(r["model"], (0, 0))
        if "error" in r:
            print(f"{r['model']:18} ERROR {r['error']}")
            continue
        print(f"{r['model']:18} {r['where']:10} {r['cold_load_s']:>7} {win_load:>6} {r['write_tok_s']:>13} {win_tok:>6}")
    for m in missing:
        print(f"{m:18} not present (pull it, or point OLLAMA_MODELS at the Windows copy)")
    target = next((r for r in results if r["model"] == BAR[0] and "error" not in r), None)
    verdict = ("not measured: the 14B wasn't present" if target is None else
               f"PASS: the 14B writes {target['write_tok_s']} tokens a second (bar {BAR[1]})" if target["write_tok_s"] >= BAR[1]
               else f"BELOW THE BAR: the 14B writes {target['write_tok_s']} tokens a second (bar {BAR[1]}); try the Vulkan backend next")
    report = {"results": results, "missing": missing, "verdict": verdict, "hardware": hardware()}
    with open("mia_gpu_bench.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("\n" + verdict)
    print("Everything is in mia_gpu_bench.json; paste it to Claude, or photograph this screen.")
    return 0 if target is not None and target["write_tok_s"] >= BAR[1] else 1


if __name__ == "__main__":
    sys.exit(main())
