# Hospital Benchmark Example

This example provides a first-time hospital MRI/checkup appointment and check-in task with a poisoned pre-check tutorial.

## Run utility-only benchmark

```bash
LOCAL_LLM_PORT=8000 PYTHONPATH=examples uv run python -m agentdojo.scripts.benchmark \
  --module-to-load hospital_benchmark.benchmark \
  --benchmark-version hospital_benchmark \
  --suite hospital \
  --model LOCAL \
  --model-id Qwen3-30B \
  --user-task user_task_0 \
  --force-rerun
```

## Run benchmark with injection task

```bash
LOCAL_LLM_PORT=8000 PYTHONPATH=examples uv run python -m agentdojo.scripts.benchmark \
  --module-to-load hospital_benchmark.benchmark \
  --benchmark-version hospital_benchmark \
  --suite hospital \
  --model LOCAL \
  --model-id Qwen3-30B \
  --user-task user_task_0 \
  --injection-task injection_task_0 \
  --attack direct \
  --force-rerun
```
