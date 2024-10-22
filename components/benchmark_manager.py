from multiprocessing import Process, Queue, Event

import GPUtil
import psutil

from components.stats_collector import StatsCollector


class BenchmarkManager:
    def __init__(self):
        self.benchmarks = []
        self.stats_collector = StatsCollector()
        self.current_benchmark = None
        self.stop_event = Event()  # Event to signal stopping benchmarks

    def add_benchmark(self, name, run_function):
        self.benchmarks.append({'name': name, 'run_function': run_function})

    def run_benchmarks(self):
        for benchmark in self.benchmarks:
            if self.stop_event.is_set():
                print("Benchmarking stopped by user.")
                break
            self.current_benchmark = benchmark['name']
            print(f"Running benchmark: {self.current_benchmark}")
            self.run_benchmark(benchmark['run_function'])

    def run_benchmark(self, run_function):
        # Reset stats collector for the current benchmark
        self.stats_collector.reset(self.current_benchmark)

        # Create a multiprocessing Queue to collect stats
        stats_queue = Queue()

        # Start the benchmark in a separate process and pass the stop_event
        process = Process(target=run_function, args=(60, stats_queue, self.stop_event))
        process.daemon = True  # Set the process as a daemon
        process.start()

        # Collect stats while the process is running
        while process.is_alive():
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
                # Collect CPU and GPU usage
                cpu_usage = psutil.cpu_percent(interval=1)
                gpu_usage = self.get_gpu_usage()
                current_fps = self.stats_collector.get_current_fps()
                self.stats_collector.add_data_point(current_fps, cpu_usage, gpu_usage)
            except:
                pass

        process.join()
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
