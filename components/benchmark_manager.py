import time
from multiprocessing import Process, Queue

import GPUtil
import psutil

from components.stats_collector import StatsCollector


class BenchmarkManager:
    def __init__(self, stop_event):
        self.benchmarks = []
        self.stats_collector = StatsCollector()
        self.current_benchmark = None
        self.stop_event = stop_event  # Use the stop_event passed from App
        self.benchmark_stopped_by_user = False  # Flag to indicate if benchmark was stopped by user

    def add_benchmark(self, name, run_function, resolution):
        self.benchmarks.append({
            'name': name,
            'run_function': run_function,
            'resolution': resolution  # Add resolution to the benchmark
        })

    def run_benchmarks(self):
        for benchmark in self.benchmarks:
            if self.stop_event.is_set() or self.benchmark_stopped_by_user:
                print("Benchmarking stopped by user.")
                break
            self.current_benchmark = benchmark['name']
            print(f"Running benchmark: {self.current_benchmark}")
            self.run_benchmark(benchmark['run_function'], benchmark['resolution'])  # Pass resolution
            if self.benchmark_stopped_by_user:
                # Stop running further benchmarks
                break

    def run_benchmark(self, run_function, resolution):
        # Reset stats collector for the current benchmark
        self.stats_collector.reset(self.current_benchmark)

        # Create a multiprocessing Queue to collect stats
        stats_queue = Queue()

        # Record the start time
        start_time = time.time()

        # Start the benchmark in a separate process and pass the stop_event and resolution
        process = Process(target=run_function, args=(5, stats_queue, self.stop_event, resolution))
        process.daemon = True  # Set the process as a daemon
        process.start()

        benchmark_running = True  # Control flag

        # Collect stats while the process is running
        while process.is_alive() and benchmark_running:
            if self.stop_event.is_set():
                print("Stopping benchmark process...")
                process.terminate()
                break
            try:
                # Non-blocking get from the queue
                while not stats_queue.empty():
                    message_type, data = stats_queue.get_nowait()
                    if message_type == 'fps':
                        self.stats_collector.set_current_fps(data)
                    elif message_type == 'stopped_by_user' and data:
                        # Benchmark was stopped by user closing renderer window
                        print("Benchmark stopped by user.")
                        self.benchmark_stopped_by_user = True
                        process.terminate()
                        benchmark_running = False  # Stop data collection
                        break  # Break inner loop

                if not benchmark_running:
                    break  # Break outer loop

                # Collect CPU and GPU usage
                cpu_usage = psutil.cpu_percent(interval=0.1)
                gpu_usage = self.get_gpu_usage()
                current_fps = self.stats_collector.get_current_fps()
                self.stats_collector.add_data_point(current_fps, cpu_usage, gpu_usage)

            except Exception as e:
                print(f"Error during data collection: {e}")
                pass

        process.join()

        # Record the end time and calculate elapsed time
        end_time = time.time()
        elapsed_time = end_time - start_time
        self.stats_collector.set_elapsed_time(self.current_benchmark, elapsed_time)

        if not self.benchmark_stopped_by_user:
            self.stats_collector.save_data(self.current_benchmark)

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

    def stop_benchmarks(self):
        self.stop_event.set()
