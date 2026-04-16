"""System and network skill for Jarvis CLI.

Commands:
  sysinfo / top          Show CPU, RAM, and battery status
  ping [host]            Check internet connectivity (default: 8.8.8.8)
  fetch <url> [name]     Download a file from a URL to the current directory
"""
from __future__ import annotations

import os
import pathlib
import platform
import re
import shlex
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from rich.console import Console
from rich.table import Table

from jarvis.core import jarvis_say, jarvis_thinking, register

_SYSTEM = platform.system().lower()

_console = Console()


def _tokens(raw: str) -> list[str]:
    parts = raw.strip().split(None, 1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------

@register("sysinfo", aliases=["top"], description="Show CPU usage, RAM, and battery status.")
def handle_sysinfo(raw: str) -> None:
    _cmd_sysinfo()


@register("ping", description="Check internet connectivity. Usage: ping [host]")
def handle_ping(raw: str) -> None:
    tokens = _tokens(raw)
    host = tokens[0] if tokens else "8.8.8.8"
    _cmd_ping(host)


@register("fetch", aliases=["download"], description="Download a file from a URL. Usage: fetch <url> [filename]")
def handle_fetch(raw: str) -> None:
    _cmd_fetch(_tokens(raw))


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------

def _cmd_sysinfo() -> None:
    with jarvis_thinking("Gathering system info..."):
        cpu_info = _get_cpu_info()
        ram_info = _get_ram_info()
        battery_info = _get_battery_info()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")

    # CPU
    table.add_row("CPU Cores", str(cpu_info["cores"]))
    load_1, load_5, load_15 = cpu_info["load"]
    table.add_row("Load Avg", f"{load_1:.2f}  {load_5:.2f}  {load_15:.2f}  [dim](1m / 5m / 15m)[/dim]")

    # RAM
    used_gb = ram_info["used"] / 1024 ** 3
    total_gb = ram_info["total"] / 1024 ** 3
    pct = ram_info["used"] / ram_info["total"] * 100 if ram_info["total"] else 0
    bar = _progress_bar(pct)
    table.add_row("RAM Used", f"{used_gb:.1f} GB / {total_gb:.1f} GB  {bar}  [dim]{pct:.0f}%[/dim]")

    # Battery
    if battery_info:
        charge = battery_info["percent"]
        status = battery_info["status"]
        batt_bar = _progress_bar(charge)
        table.add_row("Battery", f"{charge:.0f}%  {batt_bar}  [dim]{status}[/dim]")
    else:
        table.add_row("Battery", "[dim]N/A[/dim]")

    _console.print(table)


def _get_cpu_info() -> dict:
    cores = os.cpu_count() or 1
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):
        # Windows: no getloadavg — use wmic for current CPU load and fake 3 fields
        load_pct = 0.0
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "LoadPercentage", "/FORMAT:VALUE"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                if "LoadPercentage=" in line:
                    load_pct = float(line.split("=")[1].strip() or 0)
                    break
        except Exception:
            pass
        load = (load_pct, load_pct, load_pct)
    return {"cores": cores, "load": load}


def _get_ram_info() -> dict:
    total = 0
    free = 0

    if _SYSTEM == "windows":
        # Windows: ctypes GlobalMemoryStatusEx — no subprocess needed
        try:
            import ctypes
            import ctypes.wintypes

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total = stat.ullTotalPhys
            free = stat.ullAvailPhys
        except Exception:
            pass
        used = max(0, total - free)
        return {"total": total, "used": used}

    # Total via sysctl (macOS / BSD)
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=3
        )
        total = int(result.stdout.strip())
    except Exception:
        pass

    # Available pages via vm_stat (macOS): free + inactive (reclaimable)
    try:
        result = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=3)
        page_size = 4096
        free_pages = 0
        inactive_pages = 0
        for line in result.stdout.splitlines():
            m_free = re.match(r"Pages free:\s+(\d+)", line)
            m_inactive = re.match(r"Pages inactive:\s+(\d+)", line)
            if m_free:
                free_pages = int(m_free.group(1))
            if m_inactive:
                inactive_pages = int(m_inactive.group(1))
        free = (free_pages + inactive_pages) * page_size
    except Exception:
        pass

    # Fallback: /proc/meminfo (Linux)
    if total == 0:
        try:
            mem = pathlib.Path("/proc/meminfo").read_text()
            for line in mem.splitlines():
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    free = int(line.split()[1]) * 1024
        except Exception:
            pass

    used = max(0, total - free)
    return {"total": total, "used": used}


def _get_battery_info() -> dict | None:
    if _SYSTEM == "darwin":
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True, text=True, timeout=3
            )
            # Example: "\tInternalBattery-0 (id=...);\t87%; charging; ..."
            m = re.search(r"(\d+)%;\s*([^;]+)", result.stdout)
            if m:
                return {"percent": float(m.group(1)), "status": m.group(2).strip()}
        except Exception:
            pass
        return None

    if _SYSTEM == "linux":
        # Read from /sys/class/power_supply
        supply_dir = pathlib.Path("/sys/class/power_supply")
        try:
            for bat in sorted(supply_dir.iterdir()):
                cap_file = bat / "capacity"
                status_file = bat / "status"
                if cap_file.exists():
                    percent = float(cap_file.read_text().strip())
                    status = status_file.read_text().strip() if status_file.exists() else "unknown"
                    return {"percent": percent, "status": status.lower()}
        except Exception:
            pass
        return None

    if _SYSTEM == "windows":
        try:
            result = subprocess.run(
                ["wmic", "path", "Win32_Battery", "get",
                 "EstimatedChargeRemaining,BatteryStatus", "/FORMAT:VALUE"],
                capture_output=True, text=True, timeout=5,
            )
            charge = None
            status_code = None
            for line in result.stdout.splitlines():
                if "EstimatedChargeRemaining=" in line:
                    val = line.split("=")[1].strip()
                    if val:
                        charge = float(val)
                if "BatteryStatus=" in line:
                    val = line.split("=")[1].strip()
                    if val:
                        status_code = val
            if charge is not None:
                # BatteryStatus: 1=discharging, 2=AC, 3=fully charged, 6=charging
                status_map = {"1": "discharging", "2": "AC power", "3": "fully charged", "6": "charging"}
                status = status_map.get(status_code or "", "unknown")
                return {"percent": charge, "status": status}
        except Exception:
            pass
        return None

    return None


def _progress_bar(pct: float, width: int = 10) -> str:
    filled = round(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    if pct >= 80:
        color = "red"
    elif pct >= 50:
        color = "yellow"
    else:
        color = "green"
    return f"[{color}]{bar}[/{color}]"


def _cmd_ping(host: str) -> None:
    # Build platform-appropriate ping command
    if _SYSTEM == "darwin":
        cmd = ["ping", "-c", "3", "-t", "5", host]      # -t: timeout in seconds
    elif _SYSTEM == "windows":
        cmd = ["ping", "-n", "3", "-w", "5000", host]   # -n: count, -w: timeout in ms
    else:
        cmd = ["ping", "-c", "3", "-W", "5", host]      # -W: timeout in seconds (Linux)

    with jarvis_thinking(f"Pinging {host}..."):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            jarvis_say(f"[red]Ping timed out:[/red] {host}")
            return
        except FileNotFoundError:
            jarvis_say("[red]ping command not found[/red]")
            return

    # Parse packet loss — works on macOS, Linux, and Windows
    loss_match = re.search(r"(\d+(?:\.\d+)?)%\s*(?:packet\s*)?loss", output)
    loss = float(loss_match.group(1)) if loss_match else 100.0

    # Parse latency — macOS/Linux: min/avg/max; Windows: Average = Xms
    rtt_match = re.search(r"min/avg/max[^=]*=\s*([\d.]+)/([\d.]+)/([\d.]+)", output)
    win_rtt_match = re.search(r"Average\s*=\s*(\d+)ms", output)

    if loss < 100:
        if rtt_match:
            avg_ms = rtt_match.group(2)
        elif win_rtt_match:
            avg_ms = win_rtt_match.group(1)
        else:
            avg_ms = "?"
        jarvis_say(f"[green]Connected[/green] — {host}  |  avg latency [bold]{avg_ms} ms[/bold]  |  packet loss [dim]{loss:.0f}%[/dim]")
    else:
        jarvis_say(f"[red]No response[/red] from {host} — packet loss {loss:.0f}%")


def _cmd_fetch(tokens: list[str]) -> None:
    if not tokens:
        jarvis_say("Usage: fetch <url> [filename]")
        return

    url = tokens[0]
    if len(tokens) >= 2:
        filename = tokens[1]
    else:
        filename = pathlib.Path(urllib.parse.urlparse(url).path).name or "download"

    dest = pathlib.Path.cwd() / filename

    with jarvis_thinking(f"Downloading {filename}..."):
        try:
            urllib.request.urlretrieve(url, dest)
        except urllib.error.URLError as e:
            jarvis_say(f"[red]Download failed:[/red] {e.reason}")
            return
        except ValueError as e:
            jarvis_say(f"[red]Invalid URL:[/red] {e}")
            return
        except OSError as e:
            jarvis_say(f"[red]Write error:[/red] {e}")
            return

    size = dest.stat().st_size
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 ** 2:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size / 1024 ** 2:.1f} MB"

    jarvis_say(f"[green]Saved[/green] [dim]{dest}[/dim]  [dim]({size_str})[/dim]")
