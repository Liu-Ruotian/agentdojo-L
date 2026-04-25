# Agent-SAE Data Collection Extension

This repository now includes a minimally invasive Agent-SAE data collection runner implemented as wrappers around existing AgentDojo components.

## What was added

- Experiment matrix schema loader (`YAML` / `JSON`) with required run metadata.
- Risk-level sweep expansion for `-2, -1, 0, +1, +2` using a prompt pool.
- Structured trajectory logger and JSONL exporter.
- Rule-based outcome labeler module.
- Position marker module (message/character offsets with token-index placeholders).
- A toy suite (`agent_sae_toy`) for acceptance checks.
- CLI runner:

```bash
python -m agentdojo.scripts.run_agent_sae_collection \
  --suite agent_sae_toy \
  --experiment-config configs/agent_sae/toy_matrix.yaml \
  --model SCRIPTED \
  --logdir runs_agent_sae/toy \
  --force-rerun
```

## Experiment config schema

Top-level fields:
- `prompt_pool`: list of prompts keyed by risk level.
- `runs`: list of base rows. Each row includes:
  - `task_id`
  - `scenario_id`
  - `subtask_type`
  - `error_type`
  - `pressure_type`
  - `attack_template_id`
  - `attack_condition`
  - `environment_id`
  - `matched_group_id`
  - `variant_id`
  - `seed`
  - `model_name`
  - `temperature`
  - `top_p`
  - `system_prompt_id`
  - `system_prompt_risk_level`
  - `system_prompt_text`
  - `user_prompt`

## CLI options

- `--matched-group-id`: run only one matched group.
- `--risk-level`: run one or more risk levels only.
- `--max-runs`: cap number of expanded runs.
- `--force-rerun`: overwrite existing trajectory files.
- Resume behavior: existing `<trajectory_id>.json` is skipped unless `--force-rerun`.
- `--no-risk-sweep`: disable automatic sweep and use config rows as-is.

## Output format

`<logdir>/`

- `experiment_config.yaml`
- `trajectories.jsonl`
- `runs/<trajectory_id>.json`

Each trajectory contains:
- `task_metadata`
- `prompt_metadata`
- `model_metadata`
- `messages`
- `tool_calls`
- `outcome`
- `position_markers`
- `agentdojo_original_result`

## Acceptance toy run

The provided toy matrix includes:
- `1` privacy leak attack group.
- `1` low-risk mirror group.
- Prompt sweep over `5` risk levels.

This yields trajectories with required fields including:
- `matched_group_id`
- `system_prompt_risk_level`
- `error_type`
- `pressure_type`
- `tool_calls`
- `attack_success`
- `utility_success`
- `behavior_label`
- `attack_exposure` marker
- high-risk tool-call markers
