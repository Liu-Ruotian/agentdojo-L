# Airport Benchmark Example

This example provides a focused airport check-in preparation task with an injection scenario.

## Run utility-only benchmark

```bash
LOCAL_LLM_PORT=8000 PYTHONPATH=examples uv run python -m agentdojo.scripts.benchmark \
  --module-to-load airport_benchmark.benchmark \
  --benchmark-version airport_benchmark \
  --suite airport \
  --model LOCAL \
  --model-id Qwen3-30B \
  --user-task user_task_0 \
  --force-rerun
```

## Run benchmark with injection task

```bash
LOCAL_LLM_PORT=8000 PYTHONPATH=examples uv run python -m agentdojo.scripts.benchmark \
  --module-to-load airport_benchmark.benchmark \
  --benchmark-version airport_benchmark \
  --suite airport \
  --model LOCAL \
  --model-id Qwen3-30B \
  --user-task user_task_0 \
  --injection-task injection_task_0 \
  --attack direct \
  --force-rerun
```
