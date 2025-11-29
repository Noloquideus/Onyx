"""
Windows services management commands.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from pathlib import Path
import rich_click as click


@dataclass
class ServiceInfo:
    name: str
    display_name: str
    status: str
    start_type: str


def _run_powershell_json(script: str) -> Any:
    """Run a PowerShell script that returns JSON and parse it."""
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if proc.returncode != 0 or not stdout.strip():
        raise RuntimeError(stderr.strip() or "PowerShell command failed")

    # PowerShell can emit BOM or warnings; try to locate JSON start.
    out = stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Try to find first '[' or '{'
        for ch in ("[", "{"):
            idx = out.find(ch)
            if idx != -1:
                try:
                    return json.loads(out[idx:])
                except json.JSONDecodeError:
                    continue
        raise


def _get_services() -> List[ServiceInfo]:
    """Return all Windows services via PowerShell Get-Service."""
    ps = (
        "Get-Service | "
        "Select-Object Name,DisplayName,Status,StartType | "
        "ConvertTo-Json -Depth 3"
    )
    data = _run_powershell_json(ps)
    if isinstance(data, dict):
        data = [data]
    services: List[ServiceInfo] = []
    for item in data or []:
        services.append(
            ServiceInfo(
                name=item.get("Name", ""),
                display_name=item.get("DisplayName", ""),
                status=str(item.get("Status", "")),
                start_type=str(item.get("StartType", "")),
            )
        )
    return services


def _filter_services(
    services: List[ServiceInfo],
    name_substring: Optional[str],
    status: Optional[str],
    start_type: Optional[str],
) -> List[ServiceInfo]:
    name_sub = (name_substring or "").lower()
    status = status.lower() if status else None
    start_type = start_type.lower() if start_type else None

    result: List[ServiceInfo] = []
    for svc in services:
        if name_sub and (
            name_sub not in svc.name.lower()
            and name_sub not in svc.display_name.lower()
        ):
            continue
        if status and svc.status.lower() != status:
            continue
        if start_type and svc.start_type.lower() != start_type:
            continue
        result.append(svc)
    return result


def _service_control(action: str, name: str) -> None:
    """Call Windows service control via PowerShell Start-Service/Stop-Service/Restart-Service."""
    if action not in {"Start", "Stop", "Restart"}:
        raise ValueError("Invalid action")

    ps = f"{action}-Service -Name '{name}' -ErrorAction SilentlyContinue"
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        ps,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"{action}-Service failed")


@click.group()
def services() -> None:
    """Manage Windows services (list, start, stop, restart)."""


@services.command()
@click.option(
    "--name",
    "-n",
    "name_substring",
    help="Filter by name/display name substring (case-insensitive).",
)
@click.option(
    "--status",
    type=click.Choice(["Running", "Stopped", "Paused"], case_sensitive=False),
    help="Filter by service status.",
)
@click.option(
    "--start-type",
    type=click.Choice(["Automatic", "Manual", "Disabled"], case_sensitive=False),
    help="Filter by service start type.",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    help="Limit the number of displayed services.",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
    help="Output format.",
)
def list(
    name_substring: str,
    status: str,
    start_type: str,
    limit: int,
    output: str,
) -> None:
    """List Windows services with optional filters.

    Examples:
      onyx services list
      onyx services list --status Running
      onyx services list --name sql --start-type Automatic
      onyx services list --output json --limit 20
    """
    try:
        services = _get_services()
        services = _filter_services(services, name_substring, status, start_type)

        if limit and limit > 0:
            services = services[:limit]

        if not services:
            click.echo("No services matched the criteria.")
            return

        if output == "json":
            payload: List[Dict[str, Any]] = [
                {
                    "name": s.name,
                    "display_name": s.display_name,
                    "status": s.status,
                    "start_type": s.start_type,
                }
                for s in services
            ]
            click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            # Simple table output
            click.echo(
                f"{'NAME':<40} {'STATUS':<10} {'START TYPE':<12} DISPLAY NAME"
            )
            click.echo("-" * 90)
            for s in services:
                click.echo(
                    f"{s.name:<40} {s.status:<10} {s.start_type:<12} {s.display_name}"
                )
    except Exception as e:
        click.echo(f"❌ Failed to list services: {e}", err=True)


@services.command()
@click.argument("name")
def start(name: str) -> None:
    """Start a Windows service by name."""
    try:
        _service_control("Start", name)
        click.echo(f"✅ Service '{name}' start requested.")
    except Exception as e:
        click.echo(f"❌ Failed to start service '{name}': {e}", err=True)


@services.command()
@click.argument("name")
def stop(name: str) -> None:
    """Stop a Windows service by name."""
    try:
        _service_control("Stop", name)
        click.echo(f"✅ Service '{name}' stop requested.")
    except Exception as e:
        click.echo(f"❌ Failed to stop service '{name}': {e}", err=True)


@services.command()
@click.argument("name")
def restart(name: str) -> None:
    """Restart a Windows service by name."""
    try:
        _service_control("Restart", name)
        click.echo(f"✅ Service '{name}' restart requested.")
    except Exception as e:
        click.echo(f"❌ Failed to restart service '{name}': {e}", err=True)


