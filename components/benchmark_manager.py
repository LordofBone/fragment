import time
from multiprocessing import Process, Queue

from components.stats_collector import StatsCollector


class BenchmarkManager:
    def __init__(self, stop_event):
        self.benchmarks = []
        self.stats_collector = StatsCollector()
        self.current_benchmark = None
        self.stop_event = stop_event
        self.benchmark_stopped_by_user = False

    def add_benchmark(
        self,
        name,
        run_function,
        resolution,
        msaa_level=4,
        anisotropy=16,
        shadow_map_resolution=2048,
        particle_render_mode="vertex",
        vsync_enabled=True,
        sound_enabled=True,
        fullscreen=False,
    ):
        self.benchmarks.append(
            {
                "name": name,
                "run_function": run_function,
                "resolution": resolution,
                "msaa_level": msaa_level,
                "anisotropy": anisotropy,
                "shadow_map_resolution": shadow_map_resolution,
                "particle_render_mode": particle_render_mode,
                "vsync_enabled": vsync_enabled,
                "sound_enabled": sound_enabled,
                "fullscreen": fullscreen,
            }
        )

    def run_benchmarks(self):
        for benchmark in self.benchmarks:
            if self.stop_event.is_set() or self.benchmark_stopped_by_user:
                print("Benchmarking stopped by user.")
                break
            self.current_benchmark = benchmark["name"]
            print(f"Running benchmark: {self.current_benchmark}")
            self.run_benchmark(
                benchmark["run_function"],
                benchmark["resolution"],
                benchmark["msaa_level"],
                benchmark["anisotropy"],
                benchmark["shadow_map_resolution"],
                benchmark["particle_render_mode"],
                benchmark["vsync_enabled"],
                benchmark["sound_enabled"],
                benchmark["fullscreen"],
            )
            if self.benchmark_stopped_by_user:
                # Stop running further benchmarks
                break

    def run_benchmark(
        self,
        run_function,
        resolution,
        msaa_level,
        anisotropy,
        shadow_map_resolution,
        particle_render_mode,
        vsync_enabled,
        sound_enabled,
        fullscreen,
    ):
        # Create a multiprocessing Queue to collect stats
        stats_queue = Queue()

        # Start the benchmark in a separate process and pass the stop_event and resolution
        process = Process(
            target=run_function,
            args=(
                stats_queue,
                self.stop_event,
                resolution,
                msaa_level,
                anisotropy,
                shadow_map_resolution,
                particle_render_mode,
                vsync_enabled,
                sound_enabled,
                fullscreen,
            ),
        )
        process.daemon = True  # Set the process as a daemon
        process.start()

        benchmark_running = True  # Control flag
        renderer_initialized = False

        # Initialize the stats collector with the current benchmark and process PID
        self.stats_collector.reset(self.current_benchmark, process.pid)

        # Collect stats while the process is running
        while process.is_alive() and benchmark_running:
            if self.stop_event.is_set():
                print("Stopping benchmark process...")
                process.terminate()
                break
            try:
                # Check for messages from the benchmark process
                while not stats_queue.empty():
                    message_type, data = stats_queue.get_nowait()
                    if message_type == "ready":
                        renderer_initialized = True  # 3D Renderer is fully initialized
                        # Record the start time only after the renderer is ready
                        start_time = time.time()
                    elif message_type == "fps" and renderer_initialized:
                        self.stats_collector.set_current_fps(data)
                    elif message_type == "error":
                        print(f"Error in benchmark '{self.current_benchmark}': {data}")
                        self.benchmark_stopped_by_user = True
                        process.terminate()
                        benchmark_running = False  # Stop data collection
                        break  # Break inner loop
                    elif message_type == "stopped_by_user" and data:
                        # Benchmark was stopped by user closing renderer window
                        print("Benchmark stopped by user.")
                        self.benchmark_stopped_by_user = True
                        process.terminate()
                        benchmark_running = False  # Stop data collection
                        break  # Break inner loop

                if renderer_initialized:
                    # Collect CPU and GPU usage after renderer is initialized
                    # No need to sleep here; cpu_percent(interval=0.1) in add_data_point() blocks for 0.1 seconds
                    self.stats_collector.add_data_point()

            except Exception as e:
                print(f"Error during data collection: {e}")
                pass

        process.join()

        # Record the end time and calculate elapsed time only if the benchmark was initialized
        if renderer_initialized:
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.stats_collector.set_elapsed_time(self.current_benchmark, elapsed_time)

        if not self.benchmark_stopped_by_user:
            self.stats_collector.save_data(self.current_benchmark)

    def get_results(self):
        # Return the collected data
        return self.stats_collector.get_all_data()

    def calculate_performance_score(self):
        # Get all results
        results = self.stats_collector.get_all_data()

        total_avg_fps = 0
        num_benchmarks = 0

        for data in results.values():
            fps_data = data["fps_data"]
            if fps_data:
                avg_fps = sum(fps_data) / len(fps_data)
                total_avg_fps += avg_fps
                num_benchmarks += 1

        if num_benchmarks == 0:
            return 0

        # Calculate the overall average FPS
        overall_avg_fps = total_avg_fps / num_benchmarks

        # Calculate the performance score
        # For simplicity, let's define the score as the overall_avg_fps multiplied by a scaling factor
        performance_score = overall_avg_fps * 10  # You can adjust the scaling factor as needed

        # Round the score to the nearest integer
        performance_score = int(round(performance_score))

        return performance_score

    def stop_benchmarks(self):
        self.stop_event.set()
