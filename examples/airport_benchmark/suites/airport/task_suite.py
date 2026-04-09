from pathlib import Path

from agentdojo.functions_runtime import TaskEnvironment, make_function
from agentdojo.task_suite import TaskSuite
from airport_benchmark.suites.tools import AirportEnvironmentState, http_post, open_tutorial, search_web, write_file


class AirportEnvironment(TaskEnvironment):
    airport: AirportEnvironmentState


TOOLS = [search_web, open_tutorial, write_file, http_post]


task_suite = TaskSuite(
    "airport",
    AirportEnvironment,
    [make_function(tool) for tool in TOOLS],
    Path("airport_benchmark/data/suites/airport"),
)
