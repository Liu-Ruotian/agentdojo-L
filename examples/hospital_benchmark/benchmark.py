from agentdojo.task_suite import register_suite
from hospital_benchmark.suites.hospital import task_suite

benchmark_version = "hospital_benchmark"
register_suite(task_suite, benchmark_version)
