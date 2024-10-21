import threading


class StatsCollector:
    def __init__(self):
        self.benchmark_data = {}
        self.current_benchmark = None
        self.current_fps = 0
        self.lock = threading.Lock()

    def reset(self, benchmark_name):
        with self.lock:
            self.current_benchmark = benchmark_name
            self.benchmark_data[benchmark_name] = {
                'fps_data': [],
                'cpu_usage_data': [],
                'gpu_usage_data': [],
            }
            self.current_fps = 0

    def set_current_fps(self, fps):
        with self.lock:
            self.current_fps = fps

    def get_current_fps(self):
        with self.lock:
            return self.current_fps

    def add_data_point(self, fps, cpu_usage, gpu_usage):
        with self.lock:
            data = self.benchmark_data[self.current_benchmark]
            data['fps_data'].append(fps)
            data['cpu_usage_data'].append(cpu_usage)
            data['gpu_usage_data'].append(gpu_usage)

    def save_data(self, benchmark_name):
        # Optionally save data to a file
        pass

    def get_all_data(self):
        with self.lock:
            return self.benchmark_data.copy()
