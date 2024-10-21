import threading
import time
import tkinter
import tkinter.messagebox
from queue import Queue

import _tkinter
import customtkinter
import matplotlib.pyplot as plt
import matplotlib.style as plot_style
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from benchmarks.muon_shower import run_benchmark as run_muon_shower_benchmark
from benchmarks.pyramid5 import run_benchmark as run_pyramid_benchmark
from benchmarks.sphere import run_benchmark as run_sphere_benchmark
from benchmarks.tyre import run_benchmark as run_tyre_benchmark
from benchmarks.water import run_benchmark as run_water_benchmark
from benchmarks.water_pyramid import run_benchmark as run_water_pyramid_benchmark
from components.benchmark_manager import BenchmarkManager

customtkinter.set_appearance_mode("System")  # Modes: "System", "Dark", "Light"
customtkinter.set_default_color_theme("themes/314reactor.json")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.benchmark_manager = BenchmarkManager()
        self.benchmark_results = {}  # Store results for display

        # Configure window
        self.title("3D Benchmarking Tool")
        self.geometry(f"{1200}x700")

        # Configure grid layout (6 rows, 5 columns)
        self.grid_columnconfigure(0, weight=0)  # Sidebar column
        self.grid_columnconfigure((1, 2, 3, 4), weight=1)  # Main content columns
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)  # Main content rows
        self.grid_rowconfigure(4, minsize=25)  # Adjust as needed to create space
        self.grid_rowconfigure(5, weight=0)  # Row for the loading bar

        # Create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=6, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Sidebar Logo
        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="3D Benchmark",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Sidebar Buttons
        self.benchmark_button = customtkinter.CTkButton(
            self.sidebar_frame, text="Run Benchmark", command=self.run_benchmark
        )
        self.benchmark_button.grid(row=1, column=0, padx=20, pady=10)
        self.demo_button = customtkinter.CTkButton(
            self.sidebar_frame, text="Demo Mode", command=self.demo_mode
        )
        self.demo_button.grid(row=2, column=0, padx=20, pady=10)
        self.results_button = customtkinter.CTkButton(
            self.sidebar_frame, text="View Results", command=self.view_results
        )
        self.results_button.grid(row=3, column=0, padx=20, pady=10)

        # Appearance mode option menu
        self.appearance_mode_label = customtkinter.CTkLabel(
            self.sidebar_frame, text="Appearance Mode:", anchor="w"
        )
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
        )
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # UI scaling option menu
        self.scaling_label = customtkinter.CTkLabel(
            self.sidebar_frame, text="UI Scaling:", anchor="w"
        )
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
        )
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # Exit button at the bottom right
        self.exit_button = customtkinter.CTkButton(
            self.sidebar_frame, text="Exit", command=self.exit_app
        )
        self.exit_button.grid(row=9, column=0, padx=20, pady=(10, 10), sticky="se")

        # Create main content frame
        self.main_content_frame = customtkinter.CTkFrame(self)
        self.main_content_frame.grid(
            row=0, column=1, columnspan=4, rowspan=4, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)

        self.main_content_frame.grid_propagate(False)

        # Main content area (inside main_content_frame)
        self.tabview = customtkinter.CTkTabview(self.main_content_frame, width=600)
        self.tabview.grid(
            row=0, column=0, padx=0, pady=0, sticky="nsew"
        )
        self.tabview.add("Settings")
        self.tabview.add("Scenarios")
        self.tabview.add("Results")

        # Configure Results tab to expand
        self.tabview.tab("Results").grid_rowconfigure(0, weight=1)
        self.tabview.tab("Results").grid_columnconfigure(0, weight=1)

        # Graphics settings tab
        self.tabview.tab("Settings").grid_columnconfigure(0, weight=1)
        self.resolution_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="Resolution:"
        )
        self.resolution_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.resolution_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["640x480", "800x600", "1024x768", "1280x720", "1920x1080"],
        )
        self.resolution_optionmenu.grid(row=0, column=1, padx=20, pady=(20, 10))

        self.texture_quality_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="Texture Quality:"
        )
        self.texture_quality_label.grid(row=1, column=0, padx=20, pady=(20, 10))
        self.texture_quality_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"), values=["Low", "Medium", "High", "Ultra"]
        )
        self.texture_quality_optionmenu.grid(row=1, column=1, padx=20, pady=(20, 10))

        self.shadow_quality_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="Shadow Quality:"
        )
        self.shadow_quality_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        self.shadow_quality_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"), values=["Low", "Medium", "High", "Ultra"]
        )
        self.shadow_quality_optionmenu.grid(row=2, column=1, padx=20, pady=(20, 10))

        self.enable_vsync_checkbox = customtkinter.CTkCheckBox(
            self.tabview.tab("Settings"), text="Enable V-Sync"
        )
        self.enable_vsync_checkbox.grid(
            row=3, column=0, columnspan=2, padx=20, pady=(20, 10)
        )

        # Benchmark selection tab
        self.tabview.tab("Scenarios").grid_columnconfigure(0, weight=1)
        self.benchmark_list_label = customtkinter.CTkLabel(
            self.tabview.tab("Scenarios"), text="Select Benchmark Tests:"
        )
        self.benchmark_list_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # List of benchmarks
        self.benchmarks = [
            "Pyramid 5 - EMBM Test",
            "Sphere - Transparency Shader Test",
            "Tyre - Rubber Shader Test",
            "Water - Reflection Test",
            "Muon Shower",
            "Water Pyramid",
        ]

        # Dictionary to hold the state variables for each checkbox
        self.benchmark_vars = {}
        current_row = 1
        for benchmark in self.benchmarks:
            var = tkinter.BooleanVar(value=False)
            checkbox = customtkinter.CTkCheckBox(
                self.tabview.tab("Scenarios"), text=benchmark, variable=var
            )
            checkbox.grid(row=current_row, column=0, padx=20, pady=(5, 5), sticky="w")
            self.benchmark_vars[benchmark] = var
            current_row += 1

        # 'Select All' button
        self.select_all_button = customtkinter.CTkButton(
            self.tabview.tab("Scenarios"), text="Select All", command=self.select_all_benchmarks
        )
        self.select_all_button.grid(
            row=current_row, column=0, padx=20, pady=(10, 10), sticky="w"
        )
        current_row += 1

        self.deselect_all_button = customtkinter.CTkButton(
            self.tabview.tab("Scenarios"),
            text="Deselect All",
            command=self.deselect_all_benchmarks,
        )
        self.deselect_all_button.grid(
            row=current_row, column=0, padx=20, pady=(10, 10), sticky="w"
        )
        current_row += 1

        # Results tab
        self.results_textbox = customtkinter.CTkTextbox(
            self.tabview.tab("Results"), width=400, height=100
        )
        self.results_textbox.grid(row=1, column=0, padx=20, pady=(20, 20), sticky="nsew")

        # Set default values
        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")
        self.resolution_optionmenu.set("1024x768")
        self.texture_quality_optionmenu.set("High")
        self.shadow_quality_optionmenu.set("Medium")
        self.enable_vsync_checkbox.select()

        # Initialize benchmark completion queue
        self.benchmark_queue = Queue()

        # Prepare the graph canvas for results
        self.fig = None  # Will be created in display_results
        self.axs = None
        self.canvas = None

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Loading progress bar at the bottom of the right side panel
        self.loading_progress_bar = customtkinter.CTkProgressBar(self, mode="indeterminate")
        self.loading_progress_bar.grid(
            row=4, column=1, columnspan=4, padx=(20, 20), pady=(0, 10), sticky="ew"
        )
        self.loading_progress_bar.grid_remove()  # Hide it initially

    def select_all_benchmarks(self):
        for var in self.benchmark_vars.values():
            var.set(True)

    def deselect_all_benchmarks(self):
        for var in self.benchmark_vars.values():
            var.set(False)

    def run_benchmark(self):
        # Get selected benchmarks from the checkboxes
        selected_benchmarks = [
            benchmark for benchmark, var in self.benchmark_vars.items() if var.get()
        ]
        if not selected_benchmarks:
            tkinter.messagebox.showwarning("No Selection", "Please select at least one benchmark.")
            return

        # Map benchmark names to functions
        benchmark_functions = {
            "Pyramid 5 - EMBM Test": run_pyramid_benchmark,
            "Sphere - Transparency Shader Test": run_sphere_benchmark,
            "Tyre - Rubber Shader Test": run_tyre_benchmark,
            "Water - Reflection Test": run_water_benchmark,
            "Muon Shower": run_muon_shower_benchmark,
            "Water Pyramid": run_water_pyramid_benchmark,
        }

        # Clear previous results
        self.benchmark_results = {}
        self.benchmark_manager = BenchmarkManager()

        for benchmark_name in selected_benchmarks:
            if benchmark_name in benchmark_functions:
                self.benchmark_manager.add_benchmark(benchmark_name, benchmark_functions[benchmark_name])
            else:
                tkinter.messagebox.showerror("Error", f"No benchmark found for {benchmark_name}")

        # Show the loading bar
        self.show_loading_bar()

        # Run benchmarks in a separate thread to keep GUI responsive
        threading.Thread(target=self.run_benchmarks_thread, daemon=True).start()

    def run_benchmarks_thread(self):
        self.benchmark_manager.run_benchmarks()
        # Hide the loading bar
        self.after(0, self.hide_loading_bar)
        # Store results
        self.benchmark_results = self.benchmark_manager.get_results()

    def check_benchmark_status(self, benchmark_name):
        # Wait until the benchmark name appears in the queue
        while True:
            try:
                finished_benchmark = self.benchmark_queue.get(timeout=0.1)
                if finished_benchmark == benchmark_name:
                    # Check if all benchmarks are completed
                    if self.benchmark_queue.empty():
                        self.after(0, self.hide_loading_bar)
                    break
            except:
                continue

    def run_pyramid_benchmark(self):
        from benchmarks.pyramid5 import run_benchmark
        run_benchmark()
        # Signal that the benchmark has finished
        self.benchmark_queue.put("Pyramid 5 - EMBM Test")

    def run_sphere_benchmark(self):
        from benchmarks.sphere import run_benchmark
        run_benchmark()
        self.benchmark_queue.put("Sphere - Transparency Shader Test")

    def run_tyre_benchmark(self):
        from benchmarks.tyre import run_benchmark
        run_benchmark()
        self.benchmark_queue.put("Tyre - Rubber Shader Test")

    def run_water_benchmark(self):
        from benchmarks.water import run_benchmark
        run_benchmark()
        self.benchmark_queue.put("Water - Reflection Test")

    def run_muon_shower_benchmark(self):
        from benchmarks.muon_shower import run_benchmark
        run_benchmark()
        self.benchmark_queue.put("Muon Shower")

    def run_water_pyramid_benchmark(self):
        from benchmarks.water_pyramid import run_benchmark
        run_benchmark()
        self.benchmark_queue.put("Water Pyramid")

    def demo_mode(self):
        tkinter.messagebox.showinfo("Demo Mode", "Demo mode started...")

    def show_loading_bar(self):
        self.loading_progress_bar.grid()
        self.loading_progress_bar.start()

    def hide_loading_bar(self):
        self.loading_progress_bar.stop()
        self.loading_progress_bar.grid_remove()

    def run_with_loading_bar(self, func, *args, **kwargs):
        # Start timing
        start_time = time.time()
        threading.Thread(
            target=self._run_with_loading_bar_thread, args=(func, args, kwargs, start_time), daemon=True
        ).start()

    def _run_with_loading_bar_thread(self, func, args, kwargs, start_time):
        # Wait for the threshold
        threshold = 0.5  # Seconds
        while time.time() - start_time < threshold:
            time.sleep(0.1)

        # Show the loading bar if the function is still running
        self.after(0, self.show_loading_bar)

        try:
            func(*args, **kwargs)
        finally:
            self.after(0, self.hide_loading_bar)

    def view_results(self):
        # Use run_with_loading_bar to handle the loading bar with threshold
        self.run_with_loading_bar(self.generate_and_display_results)

    def generate_and_display_results(self):
        # Since we can't update Tkinter widgets from a thread, use 'after' method
        self.after(0, self.display_results)

    def display_results(self):
        plot_style.use('mpl20')  # Options are: 'mpl20': 'default', 'mpl15': 'classic'

        # Clear previous canvas if it exists
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
            self.fig = None
            self.axs = None

        # Get current appearance mode
        current_mode = customtkinter.get_appearance_mode()
        if current_mode == "Dark":
            bar_color = "skyblue"
            line_colors = ["yellow", "cyan", "magenta"]
        else:
            bar_color = "blue"
            line_colors = ["red", "green", "purple"]

        # Get collected data
        if not self.benchmark_results:
            tkinter.messagebox.showinfo("No Data", "No benchmark data available. Please run benchmarks first.")
            return

        num_benchmarks = len(self.benchmark_results)
        fig_height = 4 * num_benchmarks
        # Set squeeze=False to ensure axs is always a 2D numpy array
        self.fig, self.axs = plt.subplots(num_benchmarks, 2, figsize=(8, fig_height), squeeze=False)

        self.results_textbox.delete('1.0', tkinter.END)
        self.results_textbox.insert(tkinter.END, "Benchmark Results:\n\n")

        for idx, (benchmark_name, data) in enumerate(self.benchmark_results.items()):
            fps_data = data['fps_data']
            cpu_usage_data = data['cpu_usage_data']
            gpu_usage_data = data['gpu_usage_data']
            time_data = range(len(fps_data))

            # FPS Line Graph
            self.axs[idx, 0].plot(time_data, fps_data, color=bar_color)
            self.axs[idx, 0].set_title(f"FPS Over Time - {benchmark_name}")
            self.axs[idx, 0].set_xlabel("Time (s)")
            self.axs[idx, 0].set_ylabel("FPS")

            # CPU/GPU Usage Line Graph
            self.axs[idx, 1].plot(time_data, cpu_usage_data, label="CPU Usage", linestyle="--", color=line_colors[0])
            self.axs[idx, 1].plot(time_data, gpu_usage_data, label="GPU Usage", color=line_colors[1])
            self.axs[idx, 1].set_title(f"CPU and GPU Usage Over Time - {benchmark_name}")
            self.axs[idx, 1].set_xlabel("Time (s)")
            self.axs[idx, 1].set_ylabel("Usage (%)")
            self.axs[idx, 1].legend()

            # Insert text results
            avg_fps = sum(fps_data) / len(fps_data) if fps_data else 0
            self.results_textbox.insert(tkinter.END, f"- {benchmark_name}: {avg_fps:.2f} FPS\n")

        # Adjust colors based on appearance mode
        self.adjust_chart_mode()

        # Create a new canvas and display it
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tabview.tab("Results"))
        self.canvas.get_tk_widget().grid(row=0, column=0, padx=20, pady=(10, 0), sticky="nsew")
        self.canvas.draw()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)
        self.adjust_chart_mode()

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def adjust_chart_mode(self):
        # Get the effective appearance mode
        mode = customtkinter.get_appearance_mode()

        # If the figure and axes do not exist yet, return
        if not hasattr(self, 'fig') or not hasattr(self, 'axs') or self.fig is None or self.axs is None:
            return

        if mode == "Dark":
            chart_bg_color = "#2c2c2c"
            text_color = "#b0b0b0"
        else:
            chart_bg_color = "#f0f0f0"
            text_color = "#202020"

        # Set face color of the figure
        self.fig.patch.set_facecolor(chart_bg_color)

        # Flatten the axs array to iterate over all axes
        axes_list = self.axs.flatten() if isinstance(self.axs, np.ndarray) else [self.axs]

        # Set face color of the axes and adjust text colors
        for ax in axes_list:
            ax.set_facecolor(chart_bg_color)
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.title.set_color(text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)

        # Redraw the canvas to update the chart display
        if self.canvas is not None:
            self.canvas.draw()

    def exit_app(self):
        try:
            # Stop the loading progress bar if it's running
            if self.loading_progress_bar:
                self.loading_progress_bar.stop()

            # Cancel all pending 'after' callbacks
            after_ids = self.tk.call('after', 'info')
            for after_id in self.tk.splitlist(after_ids):
                try:
                    self.after_cancel(after_id)
                except:
                    pass

            # Close and destroy the matplotlib canvas if it exists
            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None

            # Quit the main loop
            self.quit()

            # Safely destroy the window and exit
            self.destroy()

        except _tkinter.TclError:
            # Ignore the TclError since it's non-critical and only affects cleanup
            pass
