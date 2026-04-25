from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

RiskLevel = Literal[-2, -1, 0, 1, 2]
ErrorType = Literal[
    "privacy_leak",
    "unauthorized_action",
    "irreversible_or_high_cost_action",
    "low_risk_mirror",
]
PressureType = Literal["none", "time_pressure", "authority_impersonation", "reward_inducement"]


class SystemPromptEntry(BaseModel):
    system_prompt_id: str
    system_prompt_risk_level: RiskLevel
    system_prompt_text: str


class ExperimentRunSpec(BaseModel):
    task_id: str
    scenario_id: str
    subtask_type: str
    error_type: ErrorType
    pressure_type: PressureType
    attack_template_id: str
    attack_condition: str
    environment_id: str
    matched_group_id: str
    variant_id: str
    seed: int
    model_name: str
    temperature: float
    top_p: float
    system_prompt_id: str
    system_prompt_risk_level: RiskLevel
    system_prompt_text: str
    user_prompt: str
    injection_task_id: str | None = None


class ExperimentConfig(BaseModel):
    prompt_pool: list[SystemPromptEntry] = Field(default_factory=list)
    runs: list[ExperimentRunSpec]

    @field_validator("runs")
    @classmethod
    def _non_empty_runs(cls, value: list[ExperimentRunSpec]) -> list[ExperimentRunSpec]:
        if not value:
            raise ValueError("`runs` must contain at least one entry")
        return value

    def prompt_by_risk_level(self) -> dict[int, SystemPromptEntry]:
        return {entry.system_prompt_risk_level: entry for entry in self.prompt_pool}


def load_experiment_config(path: Path) -> ExperimentConfig:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        raw = yaml.safe_load(text)
    return ExperimentConfig.model_validate(raw)


def expand_runs_with_risk_sweep(
    config: ExperimentConfig,
    enabled: bool,
    allowed_levels: set[int] | None = None,
) -> list[ExperimentRunSpec]:
    allowed_levels = allowed_levels or {-2, -1, 0, 1, 2}
    prompt_pool_by_level = config.prompt_by_risk_level()
    expanded: list[ExperimentRunSpec] = []
    for run in config.runs:
        if not enabled:
            if run.system_prompt_risk_level in allowed_levels:
                expanded.append(run)
            continue

        for risk_level in (-2, -1, 0, 1, 2):
            if risk_level not in allowed_levels:
                continue
            prompt = prompt_pool_by_level.get(risk_level)
            if prompt is None:
                prompt_id = run.system_prompt_id
                prompt_text = run.system_prompt_text
            else:
                prompt_id = prompt.system_prompt_id
                prompt_text = prompt.system_prompt_text
            expanded.append(
                run.model_copy(
                    update={
                        "variant_id": f"{run.variant_id}_r{risk_level:+d}",
                        "system_prompt_risk_level": risk_level,
                        "system_prompt_id": prompt_id,
                        "system_prompt_text": prompt_text,
                    }
                )
            )
    return expanded
