"""Run code from an employee's desk in a separate Python process with a time limit.

Every `alder/<module>.py` on the desk is imported under its short name, then each
expression is evaluated. Used by three tools: run the app, the reproduce tool and the
auditor's hidden tests. No Docker (a stretch goal), so this is a process, not a jail.
"""
import json
import subprocess
import sys

TIME_LIMIT_SECONDS = 5

_HARNESS = r'''
import ast, importlib, json, os, sys, traceback
job = json.loads(sys.stdin.read())
desk = job["desk"]
sys.path.insert(0, desk)
sys.dont_write_bytecode = True
ns, import_errors = {}, {}
for m in job["modules"]:
    try:
        ns[m] = importlib.import_module("alder." + m)
    except BaseException:
        import_errors[m] = traceback.format_exc(limit=-1).replace(desk + os.sep, "")
out = []
for expr, expected in job["checks"]:
    rec = {"expr": expr}
    try:
        val = eval(expr, dict(ns))
        rec["actual"] = repr(val)
        if expected is not None:
            rec["passed"] = (val == ast.literal_eval(expected))
    except BaseException:
        rec["error"] = traceback.format_exc(limit=-3).replace(desk + os.sep, "")
        rec["passed"] = False
    out.append(rec)
print("@@RESULT@@" + json.dumps({"results": out, "import_errors": import_errors}))
'''


def run_checks(desk_dir, modules, checks, timeout=TIME_LIMIT_SECONDS):
    """checks: list of (expression, expected_value or None). Returns dict with
    results (one per check), import_errors, and timed_out."""
    job = {"desk": str(desk_dir), "modules": list(modules),
           "checks": [(e, None if x is None else repr(x)) for e, x in checks]}
    try:
        proc = subprocess.run([sys.executable, "-I", "-c", _HARNESS], input=json.dumps(job),
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"results": [], "import_errors": {}, "timed_out": True, "stdout": ""}
    marker = proc.stdout.rfind("@@RESULT@@")
    if marker < 0:
        return {"results": [], "import_errors": {}, "timed_out": False,
                "stdout": proc.stdout[-2000:], "crash": proc.stderr[-2000:]}
    data = json.loads(proc.stdout[marker + len("@@RESULT@@"):])
    data["timed_out"] = False
    data["stdout"] = proc.stdout[:marker][-2000:]
    return data
