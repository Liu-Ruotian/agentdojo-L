from pathlib import Path

from agentdojo.functions_runtime import TaskEnvironment, make_function
from agentdojo.task_suite import TaskSuite
from hospital_benchmark.suites.tools import (
    HospitalEnvironmentState,
    get_user_profile,
    http_post,
    open_tutorial,
    search_web,
    write_file,
)


class HospitalEnvironment(TaskEnvironment):
    hospital: HospitalEnvironmentState


TOOLS = [search_web, open_tutorial, get_user_profile, write_file, http_post]


task_suite = TaskSuite(
    "hospital",
    HospitalEnvironment,
    [make_function(tool) for tool in TOOLS],
    Path("hospital_benchmark/data/suites/hospital"),
)
