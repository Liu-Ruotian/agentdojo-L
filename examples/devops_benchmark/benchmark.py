from agentdojo.task_suite import register_suite
from devops_benchmark.suites.devops import task_suite

benchmark_version = "devops_benchmark"
register_suite(task_suite, benchmark_version)
