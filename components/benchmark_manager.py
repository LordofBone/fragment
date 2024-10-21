import threading
import time

import GPUtil
import psutil

from components.stats_collector import StatsCollector


class BenchmarkManager:
    def __init__(self):
        self.benchmarks = []
        self.stats_collector = StatsCollector()
        self.current_benchmark = None

    def add_benchmark(self, name, run_function):
        self.benchmarks.append({'name': name, 'run_function': run_function})

    def run_benchmarks(self):
        for benchmark in self.benchmarks:
            self.current_benchmark = benchmark['name']
            print(f"Running benchmark: {self.current_benchmark}")
            self.run_benchmark(benchmark['run_function'])

    def run_benchmark(self, run_function):
        # Reset stats collector for the current benchmark
        self.stats_collector.reset(self.current_benchmark)

        # Start the stats collection in a separate thread
        stats_thread = threading.Thread(target=self.collect_stats)
        stats_thread.start()

        # Start the benchmark in the main thread
        run_function(duration=60, stats_collector=self.stats_collector)

        # Wait for stats collection to finish
        stats_thread.join()

        # Save the collected data
        self.stats_collector.save_data(self.current_benchmark)

    def collect_stats(self):
        # Collect stats for 60 seconds
        end_time = time.time() + 60
        while time.time() < end_time:
            fps = self.stats_collector.get_current_fps()
            cpu_usage = psutil.cpu_percent(interval=1)
            gpu_usage = self.get_gpu_usage()

            # Store the stats
            self.stats_collector.add_data_point(fps, cpu_usage, gpu_usage)

    def get_gpu_usage(self):
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]  # Assuming single GPU
            gpu_usage = gpu.load * 100  # Convert to percentage
            return gpu_usage
        else:
            return 0  # No GPU found

    def get_results(self):
        # Return the collected data
        return self.stats_collector.get_all_data()
