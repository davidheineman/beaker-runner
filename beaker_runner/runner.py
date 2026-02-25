import json
import os
from pathlib import Path

from beaker import Beaker
from rich.console import Console
from rich.table import Table

from beaker_runner.config import CommandConfig, RunnerConfig
from beaker_runner.experiment import (
    get_experiment_status,
    run_command_and_capture_experiment,
    wait_for_experiment,
)
from beaker_runner.local_env import setup_local_env

console = Console()


class Runner:
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.beaker = Beaker.from_env()
        self._venv_path = None
        self._state = self._load_state()

    # ── State persistence ──────────────────────────────────────────────

    def _state_path(self) -> Path:
        return Path(self.config.local_env_dir).resolve() / "state.json"

    def _load_state(self) -> dict:
        path = self._state_path()
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_state(self):
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._state, f, indent=2)

    # ── Venv helpers ───────────────────────────────────────────────────

    def _get_extra_env(self) -> dict:
        """Extra env vars to inject when running commands (venv activation, etc.)."""
        extra = {}
        if self._venv_path:
            venv_bin = str(self._venv_path / "bin")
            extra["VIRTUAL_ENV"] = str(self._venv_path)
            extra["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
        return extra

    # ── Main loop ──────────────────────────────────────────────────────

    def run(self):
        cfg = self.config

        console.print()
        console.print("[bold]Beaker Runner[/bold]")
        console.print(f"  Run hash:   {cfg.run_hash or '(none)'}")
        console.print(f"  Commands:   {len(cfg.commands)}")
        if cfg.repos:
            console.print(f"  Repos:      {len(cfg.repos)} (local install)")
        if cfg.dry_run:
            console.print("  [yellow]DRY RUN — commands will not be executed[/yellow]")
        console.print()

        if cfg.repos:
            console.rule("[bold]Setting up local environment[/bold]")
            self._venv_path = setup_local_env(cfg.repos, env_dir=cfg.local_env_dir)
            console.print()

        self._print_task_table()

        results = []
        for i, cmd in enumerate(cfg.commands):
            task_hash = cfg.task_hash(cmd)
            status = self._process_task(i, cmd, task_hash)
            results.append({"command": cmd.command, "hash": task_hash, "status": status})

        console.print()
        console.rule("[bold green]All tasks processed[/bold green]")
        completed = sum(1 for r in results if r["status"] == "completed")
        console.print(f"  Completed: {completed}/{len(cfg.commands)}")
        console.print()

        if cfg.state_dir:
            self._write_artifact(
                f"run-{cfg.run_hash or 'default'}.json",
                {"run_hash": cfg.run_hash, "tasks": results},
            )

    # ── Per-task logic ─────────────────────────────────────────────────

    def _process_task(self, index: int, cmd: CommandConfig, task_hash: str) -> str:
        cfg = self.config
        total = len(cfg.commands)

        console.rule(f"Task {index + 1}/{total}")
        console.print(f"  Command: {cmd.command}")
        if cmd.libs:
            console.print(f"  Libs:    {', '.join(cmd.libs)}")
        console.print(f"  Hash:    {task_hash}")

        # Check local state for a previously tracked experiment
        state_entry = self._state.get(task_hash)
        if state_entry and state_entry.get("experiment_id"):
            result = self._check_existing_experiment(state_entry, task_hash)
            if result is not None:
                return result

        if cfg.dry_run:
            console.print("  [dim]Dry run — would execute command[/dim]")
            return "dry_run"

        # Run the command locally
        env = self._get_extra_env()
        env[cfg.hash_env_var] = task_hash

        console.print("  [cyan]Running locally...[/cyan]")
        try:
            exp_name, url, exp_id = run_command_and_capture_experiment(
                command=cmd.command,
                env=env,
            )
        except RuntimeError as e:
            console.print(f"  [red]Error: {e}[/red]")
            return "failed"

        console.print(f"  Experiment: [cyan]{exp_name}[/cyan]")
        console.print(f"  URL: [link={url}]{url}[/link]")

        self._state[task_hash] = {
            "experiment_name": exp_name,
            "experiment_id": exp_id,
            "url": url,
            "status": "running",
        }
        self._save_state()

        final = wait_for_experiment(self.beaker, exp_id)

        self._state[task_hash] = {**self._state[task_hash], "status": final}
        self._save_state()

        if final == "completed":
            console.print("  [green]Task completed successfully.[/green]")
        else:
            console.print(f"  [red]Task ended with status: {final}[/red]")

        return final

    def _check_existing_experiment(self, state_entry: dict, task_hash: str) -> str | None:
        """Check a previously-tracked experiment. Returns status to use, or None to re-run."""
        exp_id = state_entry["experiment_id"]
        url = state_entry.get("url", "")

        if state_entry.get("status") == "completed":
            console.print("  [green]Already completed — skipping.[/green]")
            return "completed"

        try:
            status = get_experiment_status(self.beaker, exp_id)
        except Exception as e:
            console.print(f"  [dim]Could not check previous experiment: {e}[/dim]")
            return None

        if status == "completed":
            console.print("  [green]Previously launched experiment completed — skipping.[/green]")
            self._state[task_hash] = {**state_entry, "status": "completed"}
            self._save_state()
            return "completed"

        if status == "running":
            console.print("  [yellow]Hooking to running experiment...[/yellow]")
            console.print(f"  URL: [link={url}]{url}[/link]")
            final = wait_for_experiment(self.beaker, exp_id)
            self._state[task_hash] = {**state_entry, "status": final}
            self._save_state()
            return final

        console.print(f"  [red]Previous run {status} — re-running.[/red]")
        return None

    # ── Display helpers ────────────────────────────────────────────────

    def _print_task_table(self):
        table = Table(title="Tasks", box=None)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Hash", style="yellow", width=14)
        table.add_column("Command", style="white", overflow="fold")
        table.add_column("Status", style="green", width=12)

        for i, cmd in enumerate(self.config.commands):
            task_hash = self.config.task_hash(cmd)
            state_entry = self._state.get(task_hash)
            status = state_entry.get("status", "new") if state_entry else "new"
            display_cmd = cmd.command if len(cmd.command) <= 80 else cmd.command[:77] + "..."
            table.add_row(str(i + 1), task_hash, display_cmd, status)

        console.print(table)
        console.print()

    def _write_artifact(self, filename: str, data: dict):
        if not self.config.state_dir:
            return
        try:
            out_dir = Path(self.config.state_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / filename
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            console.print(f"  [dim]Warning: could not write to state_dir: {e}[/dim]")
