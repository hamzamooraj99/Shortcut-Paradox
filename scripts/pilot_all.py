"""Pilot every Adaption model on setups 1.6 and 2.1 (12 employees, 3 days), all models side by side.

Each model's runs go to runs_pilot_<model>/. The judge always comes from a different model family
from the employees (Writing Notes): glm-5.2 judges, except for GLM employees, where qwen3.5-397b does.
Then: python -m shortcut_paradox pilot --runs-dir runs_pilot_*
"""
import subprocess
import sys

MODELS = ["deepseek-v4-flash", "qwen3.8-27b", "gemma-4-26b-a4b-it", "gemma-4-31b-it",
          "glm-53-flash", "qwen3.5-397b", "glm-5.2"]
models = sys.argv[1:] or MODELS
procs = []
for m in models:
    judge = "qwen3.5-397b" if m.startswith("glm") else "glm-5.2"
    cmd = [sys.executable, "-m", "shortcut_paradox", "run", "--setups", "1.6,2.1", "--repeats", "1",
           "--employee", "llm", "--provider", "adaption", "--model", m, "--judge-model", judge,
           "--runs-dir", f"runs_pilot_{m}", "--days", "3"]
    log = open(f"runs_pilot_{m}.log", "a", encoding="utf-8")
    procs.append((m, subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)))
    print(f"started {m} (judge {judge})", flush=True)
for m, p in procs:
    print(f"{m}: exit {p.wait()}", flush=True)
