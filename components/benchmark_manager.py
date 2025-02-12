# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import time
from multiprocessing import Process, Queue

from components.stats_collector import StatsCollector


# ------------------------------------------------------------------------------
# BenchmarkManager Class
# ------------------------------------------------------------------------------
class BenchmarkManager:
    """
    BenchmarkManager orchestrates the running of multiple benchmark tests.

    It tracks benchmarks, collects statistics during benchmark runs via a
    separate process, and computes performance scores from the collected data.
    """

    def __init__(self, stop_event):
        # --------------------------------------------------------------------------
        # Initialization of BenchmarkManager Attributes
        # --------------------------------------------------------------------------
        self.benchmarks = []
        self.stats_collector = StatsCollector()
        self.current_benchmark = None
        self.stop_event = stop_event
        self.benchmark_stopped_by_user = False

    # --------------------------------------------------------------------------
    # Benchmark Registration
    # --------------------------------------------------------------------------
    def add_benchmark(
        self,
        name,
        run_function,
        resolution,
        msaa_level=4,
        anisotropy=16,
        shading_model="pbr",
        shadow_map_resolution=2048,
        particle_render_mode="vertex",
        vsync_enabled=True,
        sound_enabled=True,
        fullscreen=False,
    ):
        """
        Add a benchmark configuration to the list.

        Parameters:
            name (str): Benchmark name.
            run_function (callable): Function to run the benchmark.
            resolution (tuple): Window resolution.
            msaa_level (int): MSAA level.
            anisotropy (int): Anisotropic filtering level.
            shading_model (str): Shading model to use.
            shadow_map_resolution (int): Shadow map resolution.
            particle_render_mode (str): Particle render mode.
            vsync_enabled (bool): VSync enabled flag.
            sound_enabled (bool): Sound enabled flag.
            fullscreen (bool): Fullscreen mode flag.
        """
        self.benchmarks.append(
            {
                "name": name,
                "run_function": run_function,
                "resolution": resolution,
                "msaa_level": msaa_level,
                "anisotropy": anisotropy,
                "shading_model": shading_model,
                "shadow_map_resolution": shadow_map_resolution,
                "particle_render_mode": particle_render_mode,
                "vsync_enabled": vsync_enabled,
                "sound_enabled": sound_enabled,
                "fullscreen": fullscreen,
            }
        )

    # --------------------------------------------------------------------------
    # Running Benchmarks
    # --------------------------------------------------------------------------
    def run_benchmarks(self):
        """
        Run each benchmark sequentially until a stop signal is received.
        """
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
                benchmark["shading_model"],
                benchmark["shadow_map_resolution"],
                benchmark["particle_render_mode"],
                benchmark["vsync_enabled"],
                benchmark["sound_enabled"],
                benchmark["fullscreen"],
            )
            if self.benchmark_stopped_by_user:
                break

    def run_benchmark(
        self,
        run_function,
        resolution,
        msaa_level,
        anisotropy,
        shading_model,
        shadow_map_resolution,
        particle_render_mode,
        vsync_enabled,
        sound_enabled,
        fullscreen,
    ):
        """
        Run a single benchmark in a separate process and collect statistics.

        It creates a Queue to receive messages from the benchmark process, monitors
        playback and statistics until completion or an error occurs, and records the
        elapsed time.
        """
        # Create a multiprocessing Queue to collect stats
        stats_queue = Queue()

        # Start the benchmark process
        process = Process(
            target=run_function,
            args=(
                stats_queue,
                self.stop_event,
                resolution,
                msaa_level,
                anisotropy,
                shading_model,
                shadow_map_resolution,
                particle_render_mode,
                vsync_enabled,
                sound_enabled,
                fullscreen,
            ),
        )
        process.daemon = True
        process.start()

        benchmark_running = True  # Control flag for data collection
        renderer_initialized = False

        # Initialize stats collector with benchmark name and process PID
        self.stats_collector.reset(self.current_benchmark, process.pid)

        # Collect statistics while the process is running
        while process.is_alive() and benchmark_running:
            if self.stop_event.is_set():
                print("Stopping benchmark process...")
                process.terminate()
                break
            try:
                # Process messages from the benchmark process
                while not stats_queue.empty():
                    message_type, data = stats_queue.get_nowait()
                    if message_type == "ready":
                        renderer_initialized = True
                        start_time = time.time()  # Record start time when renderer is ready
                    elif message_type == "fps" and renderer_initialized:
                        self.stats_collector.set_current_fps(data)
                    elif message_type == "error":
                        print(f"Error in benchmark '{self.current_benchmark}': {data}")
                        self.benchmark_stopped_by_user = True
                        process.terminate()
                        benchmark_running = False
                        break
                    elif message_type == "stopped_by_user" and data:
                        print("Benchmark stopped by user.")
                        self.benchmark_stopped_by_user = True
                        process.terminate()
                        benchmark_running = False
                        break

                if renderer_initialized:
                    # Collect additional data (e.g., CPU/GPU usage)
                    self.stats_collector.add_data_point()

            except Exception as e:
                print(f"Error during data collection: {e}")
                pass

        process.join()

        # Calculate elapsed time if benchmark was initialized
        if renderer_initialized:
            end_time = time.time()
            elapsed_time = end_time - start_time
            self.stats_collector.set_elapsed_time(self.current_benchmark, elapsed_time)

        if not self.benchmark_stopped_by_user:
            self.stats_collector.save_data(self.current_benchmark)

    # --------------------------------------------------------------------------
    # Results and Performance Calculation
    # --------------------------------------------------------------------------
    def get_results(self):
        """Return the collected benchmark data."""
        return self.stats_collector.get_all_data()

    def calculate_performance_score(self):
        """
        Calculate an overall performance score based on the average FPS
        of all benchmarks. The score is scaled and rounded.
        """
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

        overall_avg_fps = total_avg_fps / num_benchmarks
        performance_score = overall_avg_fps * 10  # Scaling factor; adjust as needed
        return int(round(performance_score))

    # --------------------------------------------------------------------------
    # Stop Benchmarks
    # --------------------------------------------------------------------------
    def stop_benchmarks(self):
        """Signal all benchmarks to stop."""
        self.stop_event.set()
