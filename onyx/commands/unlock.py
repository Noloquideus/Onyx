"""
Unlock command to release file locks and clear restrictive attributes.
"""

from __future__ import annotations

import os
import stat
import time
import shutil
import subprocess
from pathlib import Path
from typing import List, Tuple

import click
import psutil


def _normalize(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path


def _clear_attributes_windows(target: Path) -> None:
    try:
        # Remove Read-only, Hidden, System flags using attrib
        subprocess.run([
            "attrib",
            "-R",
            "-H",
            "-S",
            str(target)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    except Exception:
        pass

    try:
        # Ensure write permission
        os.chmod(target, stat.S_IWRITE)
    except Exception:
        pass


def _clear_attributes_posix(target: Path) -> None:
    try:
        mode = target.stat().st_mode
        os.chmod(target, mode | stat.S_IWUSR)
    except Exception:
        pass

    # Remove immutable attribute if chattr exists
    if shutil.which("chattr"):
        try:
            subprocess.run(["chattr", "-i", str(target)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def _find_locking_processes(target: Path) -> List[Tuple[int, str, str]]:
    """Return list of (pid, name, file_path) that keep the target open.

    If target is a directory, includes any open file inside that directory.
    """
    results: List[Tuple[int, str, str]] = []
    target = _normalize(target)
    target_str = str(target)
    is_dir = target.is_dir()

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            for of in proc.open_files():
                fp = of.path
                if not fp:
                    continue
                if (not is_dir and os.path.samefile(fp, target_str)) or (is_dir and fp.startswith(target_str)):
                    results.append((proc.pid, proc.info.get("name") or "", fp))
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess, ProcessLookupError, FileNotFoundError):
            continue
        except Exception:
            continue
    return results


def _terminate_process(pid: int, timeout: float) -> bool:
    try:
        p = psutil.Process(pid)
        p.terminate()
        try:
            p.wait(timeout=timeout)
            return True
        except psutil.TimeoutExpired:
            p.kill()
            p.wait(timeout=timeout)
            return True
    except (psutil.NoSuchProcess, ProcessLookupError):
        return True
    except Exception:
        return False


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--force", is_flag=True, help="Force-close processes locking the file")
@click.option("--timeout", type=float, default=3.0, help="Seconds to wait for process termination")
@click.option("--recursive", is_flag=True, help="For directories: clear attributes recursively")
def unlock(path: Path, force: bool, timeout: float, recursive: bool) -> None:
    """Unlock a file or directory so it can be modified or deleted.

    - Clears read-only/hidden/system (Windows) or immutable (Linux) attributes
    - Detects processes holding file handles
    - Optionally terminates them with --force
    """

    target = _normalize(path)
    click.echo(f"🔓 Unlocking: {target}")

    # Step 1: clear attributes
    try:
        if os.name == "nt":
            if recursive and target.is_dir():
                for p in target.rglob("*"):
                    _clear_attributes_windows(p)
            _clear_attributes_windows(target)
        else:
            if recursive and target.is_dir():
                for p in target.rglob("*"):
                    _clear_attributes_posix(p)
            _clear_attributes_posix(target)
        click.echo("✅ Attributes cleared (where applicable)")
    except Exception as e:
        click.echo(f"⚠️ Could not clear attributes: {e}")

    # Step 2: find locking processes
    lockers = _find_locking_processes(target)
    if not lockers:
        click.echo("✅ No processes are locking this path")
        return

    click.echo("🚫 Locking processes detected:")
    for pid, name, fp in lockers:
        click.echo(f"   PID {pid:>6}  {name or '<unknown>'}  →  {fp}")

    if not force:
        click.echo("ℹ️  Use --force to terminate these processes")
        return

    # Step 3: terminate
    click.echo("🛑 Forcing termination...")
    ok = True
    for pid, _, _ in lockers:
        if not _terminate_process(pid, timeout):
            ok = False
    time.sleep(0.3)

    lockers_after = _find_locking_processes(target)
    if lockers_after:
        click.echo("❌ Some processes still hold the file. You may need administrator rights.")
        for pid, name, fp in lockers_after:
            click.echo(f"   PID {pid:>6}  {name or '<unknown>'}  →  {fp}")
    else:
        click.echo("✅ File unlocked. Try your operation again.")


