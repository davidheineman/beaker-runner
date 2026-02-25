### quick start

```sh
uv sync
```

```sh
brunner --config example_config.yaml
```

### how it works

1. (Optional) Clones repos and installs them into a local venv
2. Runs each command locally as a subprocess
3. Each command is expected to print a line like:
   ```
   Experiment: davidh/olmo3-600M-midtrain → https://beaker.org/ex/01KJ92NNASTF2TXHP5NCW60E13
   ```
4. The runner parses that line, then polls the Beaker experiment until it completes
5. Once complete, moves on to the next command

A per-task hash is injected as an env var (default `BEAKER_RUNNER_HASH`) so commands
can embed it in experiment names for tracking. Completed experiments are recorded in
`.beaker-runner/state.json` so re-running the same config skips finished tasks.

### example usage

```sh
# Run commands directly
brunner \
    --command "python launch_eval.py --model A" \
    --command "python launch_eval.py --model B" \
    --run-hash my-eval-v1

# Run from YAML config
brunner --config config.yaml

# Dry run (no commands executed)
brunner --config config.yaml --dry-run

# With repo setup
brunner \
    --command "python -m olmo_core.launch --config train.yaml" \
    --repo '{"url":"https://github.com/allenai/OLMo-core","branch":"main","install":"uv pip install -e .[beaker]"}' \
    --run-hash test-v1

# Custom hash env var name
brunner --config config.yaml --hash-env-var MY_RUN_HASH
```
