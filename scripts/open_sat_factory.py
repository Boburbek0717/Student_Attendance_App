"""Windows desktop launcher: restart this checkout and open its results page."""
from pathlib import Path
import ctypes
import hashlib
import json
import msvcrt
import os
import shlex
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
URL = "http://127.0.0.1:8000/"
STATE = Path(os.environ["LOCALAPPDATA"]) / "SAT Factory" / hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
HIDDEN = subprocess.CREATE_NO_WINDOW


def processes():
    # Inspect ownership before stopping anything. No elevated privileges required.
    command = r"""$ErrorActionPreference = 'Stop'
$listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
$items = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -or $_.ProcessId -in $listeners } | Select-Object ProcessId, ParentProcessId, CommandLine)
@{listeners=$listeners; processes=$items} | ConvertTo-Json -Depth 4 -Compress
"""
    shell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    result = subprocess.run([str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, check=True, timeout=20, creationflags=HIDDEN)
    return json.loads(result.stdout)


def owns(process):
    try:
        args = [item.strip('"') for item in shlex.split(process.get("CommandLine") or "", posix=False)]
        module = args.index("-m")
        if args[module + 1:module + 3] != ["uvicorn", "app.main:app"]:
            return False
        def option(name):
            return args[args.index(name) + 1]
        return (os.path.normcase(option("--app-dir")) == os.path.normcase(str(ROOT))
                and option("--host") == "127.0.0.1" and option("--port") == "8000")
    except (ValueError, IndexError):
        return False


def ready():
    try:
        # Ignore machine proxy settings for this loopback-only service.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(URL, timeout=1) as response:
            return response.status == 200 and b"SAT Factory" in response.read(32768)
    except (OSError, urllib.error.URLError):
        return False


def launch():
    if not PYTHON.is_file():
        raise RuntimeError("The project Python environment is missing. Follow the README setup instructions first.")
    snapshot = processes()
    owned = {item["ProcessId"] for item in snapshot["processes"] if owns(item)}
    if set(snapshot["listeners"]) - owned:
        raise RuntimeError("Port 8000 is being used by another server. Close that server first; nothing was stopped.")
    # Stop parent processes first; /T also stops their virtual-environment children.
    items = {item["ProcessId"]: item for item in snapshot["processes"]}
    roots = [pid for pid in owned if items[pid]["ParentProcessId"] not in owned]
    for pid in roots:
        # Recheck command identity to avoid terminating a reused process ID.
        fresh = {item["ProcessId"]: item for item in processes()["processes"]}
        if pid in fresh and owns(fresh[pid]):
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=15, creationflags=HIDDEN)
    deadline = time.monotonic() + 15
    while processes()["listeners"]:
        if time.monotonic() > deadline:
            raise RuntimeError("The previous server has not released port 8000. Please try again shortly.")
        time.sleep(0.25)
    with (STATE / "server.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([
            str(PYTHON), "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT),
            "--host", "127.0.0.1", "--port", "8000", "--no-proxy-headers",
        ], cwd=ROOT, stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=HIDDEN)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"The server could not start. Details are in {STATE / 'server.log'}")
        if ready():
            if "--no-browser" not in sys.argv:
                webbrowser.open(URL + "#results", new=2)
            return
        time.sleep(0.4)
    raise RuntimeError(f"The server is taking too long to start. Details are in {STATE / 'server.log'}")


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    # Repeated clicks cannot race two stop/start sequences.
    with (STATE / "launcher.lock").open("a+b") as lock:
        if lock.tell() == 0:
            lock.write(b"0"); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return
        try:
            launch()
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        if "--no-browser" in sys.argv:
            raise
        ctypes.windll.user32.MessageBoxW(None, str(error), "SAT Factory — could not open", 0x10)
        sys.exit(1)
