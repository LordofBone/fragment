import threading

import psutil
from GPUtil import getGPUs


class StatsCollector:
    def __init__(self):
        self.benchmark_data = {}
        self.current_benchmark = None
        self.current_fps = 0
        self.lock = threading.Lock()
        self.pid = None
        self.process = None
        self.cpu_percent_interval = 0.1  # Interval for cpu_percent(), in seconds

    def reset(self, benchmark_name, pid):
        with self.lock:
            self.current_benchmark = benchmark_name
            self.pid = pid
            self.benchmark_data[benchmark_name] = {
                'fps_data': [],
                'cpu_usage_data': [],
                'gpu_usage_data': [],
                'elapsed_time': 0
            }
            self.current_fps = 0
            # Initialize psutil.Process object
            self.process = psutil.Process(pid)
            # Prime the CPU percent calculation by making an initial call
            # This establishes a baseline for future measurements
            self.process.cpu_percent(interval=None)

    def set_current_fps(self, fps):
        with self.lock:
            self.current_fps = fps

    def get_current_fps(self):
        with self.lock:
            return self.current_fps

    def add_data_point(self):
        with self.lock:
            data = self.benchmark_data[self.current_benchmark]
            fps = self.current_fps

            # Get per-process CPU usage
            # cpu_percent(interval=0.1) blocks for 0.1 seconds and measures CPU usage over that interval
            # This provides more accurate and stable readings, reducing spikes due to instantaneous measurements
            cpu_usage = self.process.cpu_percent(interval=self.cpu_percent_interval)

            # Get the number of physical CPUs (cores)
            num_cpus = psutil.cpu_count(logical=False)
            if num_cpus is None:
                # Fallback to logical CPUs if physical count is not available
                num_cpus = psutil.cpu_count(logical=True)

            # Normalize CPU usage to match Task Manager
            # Dividing the per-process CPU usage by the number of physical CPUs gives a percentage of total capacity
            normalized_cpu_usage = cpu_usage / num_cpus

            # Ensure the value does not exceed 100%
            normalized_cpu_usage = min(normalized_cpu_usage, 100.0)

            # Get overall GPU usage across all GPUs
            gpu_usage = self.get_overall_gpu_usage()

            # Append the data points
            data['fps_data'].append(fps)
            data['cpu_usage_data'].append(normalized_cpu_usage)
            data['gpu_usage_data'].append(gpu_usage)

    def get_overall_gpu_usage(self):
        # Sum the GPU usage across all available GPUs
        total_gpu_usage = 0
        gpus = getGPUs()
        for gpu in gpus:
            total_gpu_usage += gpu.load * 100  # Convert to percentage
        return total_gpu_usage

    def set_elapsed_time(self, benchmark_name, elapsed_time):
        with self.lock:
            self.benchmark_data[benchmark_name]['elapsed_time'] = elapsed_time

    def save_data(self, benchmark_name):
        # Optionally save data to a file
        pass

    def get_all_data(self):
        with self.lock:
            return self.benchmark_data.copy()
