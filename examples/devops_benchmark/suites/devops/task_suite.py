from pathlib import Path

from agentdojo.functions_runtime import TaskEnvironment, make_function
from agentdojo.task_suite import TaskSuite
from devops_benchmark.suites.tools import (
    DevOpsEnvironmentState,
    http_post,
    open_tutorial,
    read_file,
    run_command,
    search_web,
    write_file,
)


class DevOpsEnvironment(TaskEnvironment):
    devops: DevOpsEnvironmentState


TOOLS = [run_command, read_file, write_file, http_post, search_web, open_tutorial]

task_suite = TaskSuite(
    "devops",
    DevOpsEnvironment,
    [make_function(tool) for tool in TOOLS],
    Path("devops_benchmark/data/suites/devops"),
)
