from bipelines.config import CommandConfig, RepoConfig, BipelineConfig
from bipelines.bipeline import Bipeline

config = BipelineConfig(
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
            command="python launch.py --workspace ai2/adaptability --budget ai2/oe-base --env BIPELINES_HASH=1",
            lib="simple-job",
        ),
        CommandConfig(
            command="python launch.py --workspace ai2/adaptability --budget ai2/oe-base --env BIPELINES_HASH=2",
            lib="simple-job",
        ),
        CommandConfig(
            command="python launch.py --workspace ai2/adaptability --budget ai2/oe-base --env BIPELINES_HASH=3",
            lib="simple-job",
        ),
    ],
)

bipeline = Bipeline(config)
results = bipeline.run()
