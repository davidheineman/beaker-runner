import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from rich.console import Console

from beaker_runner.config import RepoConfig

console = Console()


_UV_SEARCH_DIRS = [
    Path(sys.prefix) / "bin",
    Path.home() / ".local" / "bin",
    Path("/usr/local/bin"),
    Path.home() / ".cargo" / "bin",
]


def _find_uv() -> str | None:
    """Return the absolute path to uv, searching PATH then common install locations."""
    found = shutil.which("uv")
    if found:
        return found
    for d in _UV_SEARCH_DIRS:
        candidate = d / "uv"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def setup_local_env(
    repos: List[RepoConfig],
    env_dir: str = ".beaker-runner",
) -> Path:
    """Clone repos and install them into a local virtual environment.

    Returns the path to the virtual environment.
    """
    env_path = Path(env_dir).resolve()
    repos_path = env_path / "repos"
    venv_path = env_path / "venv"

    repos_path.mkdir(parents=True, exist_ok=True)

    uv = _find_uv()

    if not venv_path.exists():
        console.print(f"💨 Creating local venv at [cyan]{venv_path}[/cyan]...")
        if uv:
            console.print(f"  Using [cyan]uv[/cyan] ({uv})")
            subprocess.run([uv, "venv", str(venv_path)], check=True)
        else:
            console.print("  [dim]uv not found, falling back to python -m venv[/dim]")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

    venv_env = {**os.environ, "VIRTUAL_ENV": str(venv_path)}
    venv_bin = str(venv_path / "bin")
    path_parts = [venv_bin]
    if uv:
        path_parts.append(str(Path(uv).parent))
    path_parts.append(venv_env.get("PATH", ""))
    venv_env["PATH"] = ":".join(path_parts)

    for repo in repos:
        repo_path = repos_path / repo.name

        if not repo_path.exists():
            console.print(f"💨 Cloning [cyan]{repo.url}[/cyan]...")
            subprocess.run(
                ["git", "clone", repo.url, str(repo_path)],
                check=True,
            )

        if repo.commit:
            console.print(f"💨 Checking out commit [yellow]{repo.commit[:12]}[/yellow]...")
            subprocess.run(
                ["git", "checkout", repo.commit],
                cwd=str(repo_path),
                check=True,
            )
        elif repo.branch:
            console.print(f"💨 Checking out branch [yellow]{repo.branch}[/yellow]...")
            subprocess.run(
                ["git", "fetch", "origin", repo.branch],
                cwd=str(repo_path),
                check=True,
            )
            subprocess.run(
                ["git", "checkout", repo.branch],
                cwd=str(repo_path),
                check=True,
            )
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(repo_path),
                check=True,
            )

        if repo.install:
            console.print(f"💨 Installing [cyan]{repo.name}[/cyan]: {repo.install}")
            subprocess.run(
                repo.install,
                shell=True,
                cwd=str(repo_path),
                env=venv_env,
                check=True,
            )

    return venv_path
