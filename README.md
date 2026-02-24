### quick start

```sh
uv sync
```

```sh
brunner --config example_config.yaml
```

### example usage

```sh
# Run commands directly
brunner \
    --command "python eval.py --model A" \
    --command "python eval.py --model B" \
    --run-hash my-eval-v1

# Run from YAML config
brunner --config config.yaml

# Dry run (no experiments launched)
brunner --config config.yaml --dry-run

# With repo setup
brunner \
    --command "cd ~/repos/myrepo && python eval.py" \
    --repo '{"url":"https://github.com/user/myrepo","branch":"main","install":"uv pip install -e ."}' \
    --run-hash test-v1

# Save/load state for testing
brunner --config config.yaml \
    --state-dir /oe-eval-default/davidh/tmp/brunner-test
```