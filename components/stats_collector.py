import threading
import time

import psutil
from GPUtil import getGPUs


class StatsCollector:
    def __init__(self):
        self.benchmark_data = {}
        self.current_benchmark = None
        self.current_fps = 0
        self.lock = threading.Lock()

        # Shared variables for CPU and GPU usage
        self.cpu_usage = 0.0
        self.gpu_usage = 0.0
        self.usage_lock = threading.Lock()

        # Event to signal the monitoring thread to stop
        self.monitoring_event = threading.Event()

        # Start the monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_system_usage, daemon=True)
        self.monitoring_thread.start()

    def reset(self, benchmark_name, pid):
        with self.lock:
            self.current_benchmark = benchmark_name
            self.benchmark_data[benchmark_name] = {
                "fps_data": [],
                "cpu_usage_data": [],
                "gpu_usage_data": [],
                "elapsed_time": 0,
            }
            self.current_fps = 0
            # Prime the CPU percent calculation by making an initial call
            # This establishes a baseline for future measurements
            psutil.cpu_percent(interval=None)

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

            with self.usage_lock:
                cpu = self.cpu_usage
                gpu = self.gpu_usage

            # Append the data points
            data["fps_data"].append(fps)
            data["cpu_usage_data"].append(cpu)
            data["gpu_usage_data"].append(gpu)

    def monitor_system_usage(self):
        """
        Background thread to monitor CPU and GPU usage.
        Updates shared variables without blocking.
        """
        while not self.monitoring_event.is_set():
            # Fetch CPU usage
            cpu = psutil.cpu_percent(interval=None)

            # Fetch GPU usage
            try:
                gpus = getGPUs()
                if gpus:
                    gpu = sum(gpu.load * 100 for gpu in gpus)
                else:
                    gpu = 0.0
            except Exception as e:
                print(f"Error retrieving GPU usage: {e}")
                gpu = 0.0

            # Update shared variables
            with self.usage_lock:
                self.cpu_usage = cpu
                self.gpu_usage = gpu

            # Sleep for 1 second before next update
            time.sleep(1)

    def get_overall_gpu_usage(self):
        """
        Calculate the overall GPU usage across all available GPUs.

        :return: Total GPU usage as a percentage.
        """
        try:
            gpus = getGPUs()
            if not gpus:
                return 0.0
            total_gpu_usage = sum(gpu.load * 100 for gpu in gpus)
            # Clamp the value between 0 and 100
            total_gpu_usage = max(min(total_gpu_usage, 100.0), 0.0)
            return total_gpu_usage
        except Exception as e:
            print(f"Error retrieving GPU usage: {e}")
            return 0.0

    def set_elapsed_time(self, benchmark_name, elapsed_time):
        with self.lock:
            self.benchmark_data[benchmark_name]["elapsed_time"] = elapsed_time

    def save_data(self, benchmark_name):
        # Optionally save data to a file
        pass

    def get_all_data(self):
        with self.lock:
            return self.benchmark_data.copy()

    def shutdown(self):
        """Shutdown the StatsCollector and stop the monitoring thread."""
        self.monitoring_event.set()
        self.monitoring_thread.join()
