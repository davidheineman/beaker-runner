from beaker_runner.config import CommandConfig, RepoConfig, RunnerConfig
from beaker_runner.runner import Runner

config = RunnerConfig(
    run_hash="debug-batch",
    workspace="ai2/adaptability",
    repos=[
        RepoConfig(
            url="https://github.com/davidheineman/simple-job",
            branch="main",
            install="uv pip install -e .",
        ),
    ],
    commands=[
        CommandConfig(
            command="python launch.py --workspace ai2/adaptability --budget ai2/oe-base --env BRUNNER_HASH=1",
            lib="simple-job",
        ),
        CommandConfig(
            command="python launch.py --workspace ai2/adaptability --budget ai2/oe-base --env BRUNNER_HASH=2",
            lib="simple-job",
        ),
        CommandConfig(
            command="python launch.py --workspace ai2/adaptability --budget ai2/oe-base --env BRUNNER_HASH=3",
            lib="simple-job",
        ),
    ],
)

runner = Runner(config)
results = runner.run()