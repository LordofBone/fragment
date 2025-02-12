import threading
import time

import psutil
from GPUtil import getGPUs


class StatsCollector:
    """
    Collects benchmark statistics such as FPS, CPU usage, and GPU usage in background.
    """

    def __init__(self):
        """
        Initialize data structures and start the system usage monitoring thread.
        """
        # ----------------------------------------------------------------------
        # Benchmark Data
        # ----------------------------------------------------------------------
        self.benchmark_data = {}
        self.current_benchmark = None
        self.current_fps = 0

        # Thread-safety
        self.lock = threading.Lock()

        # ----------------------------------------------------------------------
        # CPU & GPU Monitoring
        # ----------------------------------------------------------------------
        self.cpu_usage = 0.0
        self.gpu_usage = 0.0
        self.usage_lock = threading.Lock()

        self.monitoring_event = threading.Event()
        self.monitoring_thread = threading.Thread(target=self.monitor_system_usage, daemon=True)
        self.monitoring_thread.start()

    # --------------------------------------------------------------------------
    # Public Methods for Benchmark Lifecycle
    # --------------------------------------------------------------------------
    def reset(self, benchmark_name, pid):
        """
        Reset data for a specific benchmark.

        Args:
            benchmark_name (str): Name of the benchmark being started.
            pid (int): Process ID (unused here, but can be stored if needed).
        """
        with self.lock:
            self.current_benchmark = benchmark_name
            self.benchmark_data[benchmark_name] = {
                "fps_data": [],
                "cpu_usage_data": [],
                "gpu_usage_data": [],
                "elapsed_time": 0,
            }
            self.current_fps = 0
            # Initialize CPU usage measurement
            psutil.cpu_percent(interval=None)

    def set_current_fps(self, fps):
        """
        Update the current FPS measurement.

        Args:
            fps (float): Current frames per second.
        """
        with self.lock:
            self.current_fps = fps

    def get_current_fps(self):
        """
        Retrieve the current FPS measurement.

        Returns:
            float: The most recent recorded FPS.
        """
        with self.lock:
            return self.current_fps

    def add_data_point(self):
        """
        Record a data point (FPS, CPU, GPU) in the current benchmark's arrays.
        """
        with self.lock:
            data = self.benchmark_data[self.current_benchmark]
            fps = self.current_fps

            with self.usage_lock:
                cpu = self.cpu_usage
                gpu = self.gpu_usage

            data["fps_data"].append(fps)
            data["cpu_usage_data"].append(cpu)
            data["gpu_usage_data"].append(gpu)

    def set_elapsed_time(self, benchmark_name, elapsed_time):
        """
        Store the benchmark's total elapsed time.

        Args:
            benchmark_name (str): Which benchmark's time to set.
            elapsed_time (float): Total elapsed time in seconds.
        """
        with self.lock:
            self.benchmark_data[benchmark_name]["elapsed_time"] = elapsed_time

    def get_all_data(self):
        """
        Retrieve a copy of all benchmark data.

        Returns:
            dict: Deep copy of the benchmark data dictionary.
        """
        with self.lock:
            return self.benchmark_data.copy()

    def save_data(self, benchmark_name):
        """
        Optionally save data to a file or database.
        (Currently empty placeholder; can be implemented as needed.)
        """
        pass

    def shutdown(self):
        """
        Stop the usage monitoring thread and clean up.
        """
        self.monitoring_event.set()
        self.monitoring_thread.join()

    # --------------------------------------------------------------------------
    # Background Monitoring Thread
    # --------------------------------------------------------------------------
    def monitor_system_usage(self):
        """
        Continuously monitor CPU/GPU usage and update shared variables.
        """
        while not self.monitoring_event.is_set():
            # CPU usage
            cpu = psutil.cpu_percent(interval=None)

            # GPU usage
            try:
                gpus = getGPUs()
                if gpus:
                    gpu = sum(gpu.load * 100 for gpu in gpus)
                else:
                    gpu = 0.0
            except Exception as e:
                print(f"Error retrieving GPU usage: {e}")
                gpu = 0.0

            # Update shared usage
            with self.usage_lock:
                self.cpu_usage = cpu
                self.gpu_usage = gpu

            time.sleep(1)

    # --------------------------------------------------------------------------
    # Optional Extra Method
    # --------------------------------------------------------------------------
    def get_overall_gpu_usage(self):
        """
        Compute the overall GPU usage across all GPUs.

        Returns:
            float: Total GPU usage in percentage (clamped 0-100).
        """
        try:
            gpus = getGPUs()
            if not gpus:
                return 0.0
            total_gpu_usage = sum(gpu.load * 100 for gpu in gpus)
            total_gpu_usage = max(min(total_gpu_usage, 100.0), 0.0)
            return total_gpu_usage
        except Exception as e:
            print(f"Error retrieving GPU usage: {e}")
            return 0.0
