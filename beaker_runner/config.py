import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import yaml


@dataclass
class RepoConfig:
    """A git repository to clone and install into the local environment."""

    url: str
    branch: str = "main"
    commit: Optional[str] = None
    install: Optional[str] = None
    path: Optional[str] = None

    @property
    def name(self) -> str:
        return self.url.rstrip("/").split("/")[-1].removesuffix(".git")


@dataclass
class CommandConfig:
    """A command to run locally that launches a Beaker experiment."""

    command: str
    libs: List[str] = field(default_factory=list)


@dataclass
class RunnerConfig:
    """Main configuration for the beaker-runner orchestrator."""

    commands: List[CommandConfig]
    repos: List[RepoConfig] = field(default_factory=list)

    run_hash: str = ""
    hash_env_var: str = "BEAKER_RUNNER_HASH"

    local_env_dir: str = ".beaker-runner"
    state_dir: Optional[str] = None
    dry_run: bool = False

    @property
    def repo_lookup(self) -> Dict[str, RepoConfig]:
        return {r.name: r for r in self.repos}

    def validate(self):
        """Check that all libs referenced by commands exist in repos."""
        repo_names = {r.name for r in self.repos}
        for cmd in self.commands:
            for lib in cmd.libs:
                if lib not in repo_names:
                    raise ValueError(
                        f"Command references unknown lib '{lib}'. "
                        f"Available repos: {', '.join(sorted(repo_names))}"
                    )

    def task_hash(self, cmd: CommandConfig) -> str:
        """Deterministic hash for deduplication: command + run_hash."""
        content = f"{cmd.command}|{self.run_hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]


def load_config_from_yaml(path: str) -> RunnerConfig:
    with open(path) as f:
        data = yaml.safe_load(f)

    kwargs = {k: v for k, v in data.items() if k not in ("repos", "commands")}
    kwargs["repos"] = [RepoConfig(**r) for r in data.get("repos", [])]

    commands = []
    for c in data.get("commands", []):
        if isinstance(c, str):
            commands.append(CommandConfig(command=c))
        elif isinstance(c, dict):
            commands.append(CommandConfig(**c))
        else:
            raise ValueError(f"Invalid command entry: {c!r}")
    kwargs["commands"] = commands

    config = RunnerConfig(**kwargs)
    config.validate()
    return config
