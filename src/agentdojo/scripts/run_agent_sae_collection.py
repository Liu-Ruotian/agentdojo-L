from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import click

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor
from agentdojo.agent_sae.outcome_labeler import label_outcome
from agentdojo.agent_sae.position_markers import mark_positions
from agentdojo.agent_sae.schema import expand_runs_with_risk_sweep, load_experiment_config
from agentdojo.agent_sae.scripted_agent import AgentSAEScriptedPolicy
from agentdojo.agent_sae.toy_suite import agent_sae_toy_suite, build_toy_environment
from agentdojo.agent_sae.trajectory_logging import HIGH_RISK_TOOLS, extract_tool_calls
from agentdojo.base_tasks import BaseInjectionTask
from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import ChatMessage, get_text_content_as_str


class FixedArgsAgentPipeline(BasePipelineElement):
    def __init__(self, elements: list[BasePipelineElement], fixed_extra_args: dict, name: str):
        self.elements = elements
        self.fixed_extra_args = fixed_extra_args
        self.name = name

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: list[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, list[ChatMessage], dict]:
        merged_args = {**self.fixed_extra_args, **extra_args}
        for element in self.elements:
            query, runtime, env, messages, merged_args = element.query(query, runtime, env, messages, merged_args)
        return query, runtime, env, messages, merged_args


def sanitize_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-+]", "_", value)


def serialize_message(message: ChatMessage) -> dict:
    out = dict(message)
    if message.get("tool_call") is not None:
        out["tool_call"] = message["tool_call"].model_dump()
    if message.get("tool_calls") is not None:
        out["tool_calls"] = [tool_call.model_dump() for tool_call in message["tool_calls"] or []]
    return out


def _load_suite(suite_name: str, benchmark_version: str):
    if suite_name == "agent_sae_toy":
        return agent_sae_toy_suite
    return get_suite(benchmark_version, suite_name)


def _pick_injection_task_id(run_spec_dict: dict, suite) -> str:
    if run_spec_dict.get("injection_task_id"):
        return run_spec_dict["injection_task_id"]
    if run_spec_dict["error_type"] == "privacy_leak":
        return "injection_task_1"
    if run_spec_dict["error_type"] == "low_risk_mirror":
        return "injection_task_2"
    return next(iter(suite.injection_tasks.keys()))


@click.command()
@click.option("--suite", type=str, required=True)
@click.option("--benchmark-version", type=str, default="v1.2.2")
@click.option("--experiment-config", type=click.Path(path_type=Path), required=True)
@click.option("--model", type=str, default="SCRIPTED")
@click.option("--model-id", type=str, default=None)
@click.option("--logdir", type=click.Path(path_type=Path), required=True)
@click.option("--matched-group-id", type=str, default=None)
@click.option("--risk-level", type=int, multiple=True, default=tuple())
@click.option("--max-runs", type=int, default=None)
@click.option("--decision-window-tokens", type=int, default=64)
@click.option("--no-risk-sweep", is_flag=True)
@click.option("--force-rerun", is_flag=True)
def main(
    suite: str,
    benchmark_version: str,
    experiment_config: Path,
    model: str,
    model_id: str | None,
    logdir: Path,
    matched_group_id: str | None,
    risk_level: tuple[int, ...],
    max_runs: int | None,
    decision_window_tokens: int,
    no_risk_sweep: bool,
    force_rerun: bool,
):
    config = load_experiment_config(experiment_config)
    suite_obj = _load_suite(suite, benchmark_version)

    allowed_levels = set(risk_level) if risk_level else None
    runs = expand_runs_with_risk_sweep(config, enabled=not no_risk_sweep, allowed_levels=allowed_levels)
    if matched_group_id is not None:
        runs = [run for run in runs if run.matched_group_id == matched_group_id]
    if max_runs is not None:
        runs = runs[:max_runs]

    logdir.mkdir(parents=True, exist_ok=True)
    runs_dir = logdir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(experiment_config, logdir / "experiment_config.yaml")
    jsonl_path = logdir / "trajectories.jsonl"
    if force_rerun and jsonl_path.exists():
        jsonl_path.unlink()

    for run in runs:
        run_dict = run.model_dump()
        trajectory_id = sanitize_id(
            f"{run.matched_group_id}_{run.task_id}_{run.error_type}_r{run.system_prompt_risk_level:+d}_{run.seed}_{run.variant_id}"
        )
        run_output_path = runs_dir / f"{trajectory_id}.json"
        if run_output_path.exists() and not force_rerun:
            continue

        user_task = suite_obj.get_user_task_by_id(run.task_id)
        injection_task_id = _pick_injection_task_id(run_dict, suite_obj)
        injection_task: BaseInjectionTask = suite_obj.get_injection_task_by_id(injection_task_id)

        if model.upper() == "SCRIPTED":
            pipeline = FixedArgsAgentPipeline(
                elements=[
                    SystemMessage(run.system_prompt_text),
                    InitQuery(),
                    AgentSAEScriptedPolicy(),
                    ToolsExecutionLoop([ToolsExecutor(), AgentSAEScriptedPolicy()]),
                ],
                fixed_extra_args={"run_spec": run_dict},
                name=f"scripted-{run.model_name}",
            )
        else:
            pipeline = AgentPipeline.from_config(
                PipelineConfig(
                    llm=model,
                    model_id=model_id,
                    defense=None,
                    tool_delimiter="tool",
                    system_message_name=None,
                    system_message=run.system_prompt_text,
                    tool_output_format="yaml",
                )
            )

        environment = build_toy_environment(run.attack_condition) if suite == "agent_sae_toy" else None
        utility, security = suite_obj.run_task_with_pipeline(
            pipeline,
            user_task,
            injection_task,
            injections={},
            environment=environment,
        )

        env = environment if environment is not None else suite_obj.load_and_inject_default_environment({})
        _, _, _, messages, _ = pipeline.query(run.user_prompt, runtime=FunctionsRuntime(suite_obj.tools), env=env)

        serialized_messages = [serialize_message(message) for message in messages]
        tool_calls = extract_tool_calls(messages)

        assistant_messages = [message for message in messages if message["role"] == "assistant" and message.get("content")]
        final_assistant_text = get_text_content_as_str(assistant_messages[-1]["content"]) if assistant_messages else ""
        outcome = label_outcome(run, utility=utility, security=security, tool_calls=tool_calls, final_assistant_text=final_assistant_text)
        positions = mark_positions(messages, high_risk_tool_names=HIGH_RISK_TOOLS, decision_window_tokens=decision_window_tokens)

        payload = {
            "trajectory_id": trajectory_id,
            "task_metadata": {
                "task_id": run.task_id,
                "injection_task_id": injection_task_id,
                "scenario_id": run.scenario_id,
                "subtask_type": run.subtask_type,
                "user_task_metadata": getattr(user_task, "metadata", {}),
                "injection_task_metadata": getattr(injection_task, "metadata", {}),
            },
            "prompt_metadata": {
                "matched_group_id": run.matched_group_id,
                "variant_id": run.variant_id,
                "error_type": run.error_type,
                "pressure_type": run.pressure_type,
                "attack_template_id": run.attack_template_id,
                "attack_condition": run.attack_condition,
                "system_prompt_id": run.system_prompt_id,
                "system_prompt_risk_level": run.system_prompt_risk_level,
                "system_prompt_text": run.system_prompt_text,
                "user_prompt": run.user_prompt,
            },
            "model_metadata": {
                "model_name": run.model_name,
                "model": model,
                "model_id": model_id,
                "temperature": run.temperature,
                "top_p": run.top_p,
                "seed": run.seed,
                "environment_id": run.environment_id,
            },
            "messages": serialized_messages,
            "tool_calls": tool_calls,
            "outcome": outcome,
            "position_markers": positions,
            "agentdojo_original_result": {"utility": utility, "security": security},
            "run_spec": run_dict,
        }

        run_output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
