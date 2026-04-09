from agentdojo.task_suite import register_suite
from airport_benchmark.suites.airport import task_suite

benchmark_version = "airport_benchmark"
register_suite(task_suite, benchmark_version)
