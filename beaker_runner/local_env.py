import os
import subprocess
from pathlib import Path
from typing import List

from rich.console import Console

from beaker_runner.config import RepoConfig

console = Console()


def setup_local_env(
    repos: List[RepoConfig],
    env_dir: str = ".beaker-runner",
) -> Path:
    """Clone repos and install them into a local uv virtual environment.

    Returns the path to the virtual environment.
    """
    env_path = Path(env_dir).resolve()
    repos_path = env_path / "repos"
    venv_path = env_path / "venv"

    repos_path.mkdir(parents=True, exist_ok=True)

    if not venv_path.exists():
        console.print(f"💨 Creating local venv at [cyan]{venv_path}[/cyan]...")
        subprocess.run(["uv", "venv", str(venv_path)], check=True)

    venv_env = {**os.environ, "VIRTUAL_ENV": str(venv_path)}
    venv_bin = str(venv_path / "bin")
    venv_env["PATH"] = f"{venv_bin}:{venv_env.get('PATH', '')}"

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
