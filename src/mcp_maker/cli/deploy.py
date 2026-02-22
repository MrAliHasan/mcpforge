"""
MCP-Maker Deploy Command — Generate deployment configs for Railway, Render, and Fly.io.

Usage:
    mcp-maker deploy --platform railway
    mcp-maker deploy --platform render
    mcp-maker deploy --platform fly
"""

import os
import json
import sys

import typer
from rich.console import Console
from rich.panel import Panel

from .main import app, console


@app.command()
def deploy(
    platform: str = typer.Option(
        "railway",
        "--platform", "-p",
        help="Deployment platform. Options: railway, render, fly.",
    ),
    server_file: str = typer.Option(
        "mcp_server.py",
        "--file", "-f",
        help="Path to the generated server file.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Port to expose the server on.",
    ),
):
    """🚀 Generate deployment files for your MCP server.

    Creates a Dockerfile, requirements.txt, and platform-specific config
    for one-command deployment to Railway, Render, or Fly.io.
    """
    if not os.path.isfile(server_file):
        console.print(f"  [red]✗[/red] Server file not found: {server_file}")
        console.print("  [dim]Run [cyan]mcp-maker init <source>[/cyan] first to generate a server.[/dim]")
        raise typer.Exit(1)

    platform = platform.lower().strip()
    if platform not in ("railway", "render", "fly"):
        console.print(f"  [red]✗[/red] Unsupported platform: {platform}")
        console.print("  [dim]Supported: railway, render, fly[/dim]")
        raise typer.Exit(1)

    generated_files = []

    # 1. Generate requirements.txt
    requirements = _detect_requirements(server_file)
    _write_file("requirements.txt", "\n".join(requirements) + "\n")
    generated_files.append("requirements.txt")

    # 2. Generate Dockerfile
    dockerfile = _generate_dockerfile(server_file, port)
    _write_file("Dockerfile", dockerfile)
    generated_files.append("Dockerfile")

    # 3. Generate platform config
    if platform == "railway":
        config = _generate_railway_config(port)
        _write_file("railway.json", json.dumps(config, indent=2) + "\n")
        generated_files.append("railway.json")
    elif platform == "render":
        config = _generate_render_config(server_file, port)
        _write_file("render.yaml", config)
        generated_files.append("render.yaml")
    elif platform == "fly":
        config = _generate_fly_config(server_file, port)
        _write_file("fly.toml", config)
        generated_files.append("fly.toml")

    # 4. Generate .dockerignore
    dockerignore = _generate_dockerignore()
    _write_file(".dockerignore", dockerignore)
    generated_files.append(".dockerignore")

    # Print success
    console.print()
    console.print(Panel(
        "\n".join([f"  📄 {f}" for f in generated_files]),
        title=f"[bold green]✓ {platform.title()} deployment files generated[/bold green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()

    if platform == "railway":
        console.print("  [bold]Next steps:[/bold]")
        console.print("  1. [cyan]railway login[/cyan]")
        console.print("  2. [cyan]railway init[/cyan]")
        console.print("  3. [cyan]railway up[/cyan]")
        console.print()
        console.print("  [dim]Set environment variables in the Railway dashboard.[/dim]")
    elif platform == "render":
        console.print("  [bold]Next steps:[/bold]")
        console.print("  1. Push to GitHub/GitLab")
        console.print("  2. Connect repo in [cyan]render.com[/cyan] dashboard")
        console.print("  3. Render will auto-deploy from render.yaml")
    elif platform == "fly":
        console.print("  [bold]Next steps:[/bold]")
        console.print("  1. [cyan]fly auth login[/cyan]")
        console.print("  2. [cyan]fly launch[/cyan]")
        console.print("  3. [cyan]fly deploy[/cyan]")
        console.print()
        console.print("  [dim]Set secrets with: [cyan]fly secrets set KEY=VALUE[/cyan][/dim]")


def _write_file(filename: str, content: str):
    """Write a file, warn if overwriting."""
    if os.path.exists(filename):
        console.print(f"  [yellow]⚠[/yellow] Overwriting {filename}")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def _detect_requirements(server_file: str) -> list[str]:
    """Auto-detect required packages from the generated server code."""
    with open(server_file, "r", encoding="utf-8") as f:
        code = f.read()

    # Also read autogen file if it exists
    autogen_file = os.path.join(os.path.dirname(server_file), "_autogen_mcp_server.py")
    if os.path.isfile(autogen_file):
        with open(autogen_file, "r", encoding="utf-8") as f:
            code += "\n" + f.read()

    reqs = ["mcp>=1.0.0"]  # Always needed

    import_map = {
        "import sqlite3": None,  # Built-in
        "import psycopg2": "psycopg2-binary>=2.9.0",
        "import pymysql": "pymysql>=1.1.0",
        "import pymongo": "pymongo>=4.6.0",
        "from supabase": "supabase>=2.0.0",
        "import openpyxl": "openpyxl>=3.1.0",
        "import aiosqlite": "aiosqlite>=0.20.0",
        "import asyncpg": "asyncpg>=0.29.0",
        "import aiomysql": "aiomysql>=0.2.0",
        "import httpx": "httpx>=0.27.0",
        "import chromadb": "chromadb>=0.5.0",
        "from pyairtable": "pyairtable>=2.0.0",
        "import gspread": "gspread>=6.0.0",
        "from notion_client": "notion-client>=2.0.0",
    }

    for import_str, pkg in import_map.items():
        if import_str in code and pkg:
            reqs.append(pkg)

    return sorted(set(reqs))


def _generate_dockerfile(server_file: str, port: int) -> str:
    """Generate a production Dockerfile."""
    return f"""# Auto-generated by MCP-Maker
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY {server_file} .
COPY _autogen_mcp_server.py .
COPY .env* ./

# Expose port
EXPOSE {port}

# Run the MCP server
CMD ["python", "{server_file}"]
"""


def _generate_dockerignore() -> str:
    """Generate a .dockerignore file."""
    return """__pycache__
*.pyc
*.pyo
.git
.gitignore
.venv
venv
.env.local
*.md
.mcp-maker.lock
"""


def _generate_railway_config(port: int) -> dict:
    """Generate railway.json config."""
    return {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {
            "builder": "DOCKERFILE",
            "dockerfilePath": "Dockerfile",
        },
        "deploy": {
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 10,
        },
    }


def _generate_render_config(server_file: str, port: int) -> str:
    """Generate render.yaml (Render Blueprint)."""
    return f"""# Auto-generated by MCP-Maker
services:
  - type: web
    name: mcp-server
    runtime: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: PORT
        value: "{port}"
"""


def _generate_fly_config(server_file: str, port: int) -> str:
    """Generate fly.toml config."""
    return f"""# Auto-generated by MCP-Maker
app = "mcp-server"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = {port}
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 256
"""
