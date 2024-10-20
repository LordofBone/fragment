import threading
import tkinter
import tkinter.messagebox
from queue import Queue

import _tkinter
import customtkinter
import matplotlib.pyplot as plt
import matplotlib.style as plot_style
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("themes/314reactor.json")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # Configure window
        self.title("3D Benchmarking Tool")
        self.geometry(f"{1200}x700")

        # Configure grid layout (5x5)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3, 4), weight=0)
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)

        # Create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Sidebar Logo
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="3D Benchmark",
                                                 font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Sidebar Buttons
        self.benchmark_button = customtkinter.CTkButton(self.sidebar_frame, text="Run Benchmark",
                                                        command=self.run_benchmark)
        self.benchmark_button.grid(row=1, column=0, padx=20, pady=10)
        self.demo_button = customtkinter.CTkButton(self.sidebar_frame, text="Demo Mode", command=self.demo_mode)
        self.demo_button.grid(row=2, column=0, padx=20, pady=10)
        self.results_button = customtkinter.CTkButton(self.sidebar_frame, text="View Results",
                                                      command=self.view_results)
        self.results_button.grid(row=3, column=0, padx=20, pady=10)

        # Appearance mode option menu
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                                       values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # UI scaling option menu
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame,
                                                               values=["80%", "90%", "100%", "110%", "120%"],
                                                               command=self.change_scaling_event)
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # Exit button at the bottom right
        self.exit_button = customtkinter.CTkButton(self.sidebar_frame, text="Exit", command=self.exit_app)
        self.exit_button.grid(row=9, column=0, padx=20, pady=(10, 10), sticky="se")

        # Main content area
        self.tabview = customtkinter.CTkTabview(self, width=600)
        self.tabview.grid(row=0, column=1, columnspan=4, rowspan=5, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.tabview.add("Settings")
        self.tabview.add("Scenarios")
        self.tabview.add("Results")

        # Configure Results tab to expand
        self.tabview.tab("Results").grid_rowconfigure(0, weight=1)
        self.tabview.tab("Results").grid_columnconfigure(0, weight=1)

        # Graphics settings tab
        self.tabview.tab("Settings").grid_columnconfigure(0, weight=1)
        self.resolution_label = customtkinter.CTkLabel(self.tabview.tab("Settings"), text="Resolution:")
        self.resolution_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.resolution_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Settings"),
                                                                 values=["640x480", "800x600", "1024x768", "1280x720",
                                                                         "1920x1080"])
        self.resolution_optionmenu.grid(row=0, column=1, padx=20, pady=(20, 10))

        self.texture_quality_label = customtkinter.CTkLabel(self.tabview.tab("Settings"),
                                                            text="Texture Quality:")
        self.texture_quality_label.grid(row=1, column=0, padx=20, pady=(20, 10))
        self.texture_quality_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Settings"),
                                                                      values=["Low", "Medium", "High", "Ultra"])
        self.texture_quality_optionmenu.grid(row=1, column=1, padx=20, pady=(20, 10))

        self.shadow_quality_label = customtkinter.CTkLabel(self.tabview.tab("Settings"),
                                                           text="Shadow Quality:")
        self.shadow_quality_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        self.shadow_quality_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Settings"),
                                                                     values=["Low", "Medium", "High", "Ultra"])
        self.shadow_quality_optionmenu.grid(row=2, column=1, padx=20, pady=(20, 10))

        self.enable_vsync_checkbox = customtkinter.CTkCheckBox(self.tabview.tab("Settings"),
                                                               text="Enable V-Sync")
        self.enable_vsync_checkbox.grid(row=3, column=0, columnspan=2, padx=20, pady=(20, 10))

        # Benchmark selection tab
        self.tabview.tab("Scenarios").grid_columnconfigure(0, weight=1)
        self.benchmark_list_label = customtkinter.CTkLabel(self.tabview.tab("Scenarios"),
                                                           text="Select Benchmark Tests:")
        self.benchmark_list_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # List of benchmarks
        self.benchmarks = ["Pyramid 5 - EMBM Test", "Sphere - Transparency Shader Test",
                           "Tyre - Rubber Shader Test", "Water - Reflection Test",
                           "Muon Shower", "Water Pyramid"]

        # Dictionary to hold the state variables for each checkbox
        self.benchmark_vars = {}
        current_row = 1
        for benchmark in self.benchmarks:
            var = tkinter.BooleanVar(value=False)
            checkbox = customtkinter.CTkCheckBox(self.tabview.tab("Scenarios"), text=benchmark, variable=var)
            checkbox.grid(row=current_row, column=0, padx=20, pady=(5, 5), sticky="w")
            self.benchmark_vars[benchmark] = var
            current_row += 1

        # 'Select All' button
        self.select_all_button = customtkinter.CTkButton(self.tabview.tab("Scenarios"), text="Select All",
                                                         command=self.select_all_benchmarks)
        self.select_all_button.grid(row=current_row, column=0, padx=20, pady=(10, 10), sticky="w")
        current_row += 1

        self.deselect_all_button = customtkinter.CTkButton(self.tabview.tab("Scenarios"), text="Deselect All",
                                                           command=self.deselect_all_benchmarks)
        self.deselect_all_button.grid(row=current_row, column=0, padx=20, pady=(10, 10), sticky="w")
        current_row += 1

        # Progress bar for benchmark loading
        self.loading_progress_bar = customtkinter.CTkProgressBar(self.tabview.tab("Scenarios"),
                                                                 mode="indeterminate")
        self.loading_progress_bar.grid(row=current_row, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.loading_progress_bar.grid_remove()  # Hide it initially

        # Results tab
        self.results_textbox = customtkinter.CTkTextbox(self.tabview.tab("Results"), width=400, height=100)
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

    def select_all_benchmarks(self):
        for var in self.benchmark_vars.values():
            var.set(True)

    def deselect_all_benchmarks(self):
        for var in self.benchmark_vars.values():
            var.set(False)

    def run_benchmark(self):
        # Get selected benchmarks from the checkboxes
        selected_benchmarks = [benchmark for benchmark, var in self.benchmark_vars.items() if var.get()]
        if not selected_benchmarks:
            tkinter.messagebox.showwarning("No Selection", "Please select at least one benchmark.")
            return

        # Map benchmark names to functions
        benchmark_functions = {
            "Pyramid 5 - EMBM Test": self.run_pyramid_benchmark,
            "Sphere - Transparency Shader Test": self.run_sphere_benchmark,
            "Tyre - Rubber Shader Test": self.run_tyre_benchmark,
            "Water - Reflection Test": self.run_water_benchmark,
            "Muon Shower": self.run_muon_shower_benchmark,
            "Water Pyramid": self.run_water_pyramid_benchmark,
        }

        for benchmark_name in selected_benchmarks:
            if benchmark_name in benchmark_functions:
                # Show the progress bar
                self.loading_progress_bar.grid()
                self.loading_progress_bar.start()

                # In run_benchmark method
                threading.Thread(target=benchmark_functions[benchmark_name], daemon=True).start()

                # In check_benchmark_status method
                threading.Thread(target=self.check_benchmark_status, args=(benchmark_name,), daemon=True).start()

            else:
                tkinter.messagebox.showerror("Error", f"No benchmark found for {benchmark_name}")

    def check_benchmark_status(self, benchmark_name):
        # Wait until the benchmark name appears in the queue
        while True:
            try:
                finished_benchmark = self.benchmark_queue.get(timeout=0.1)
                if finished_benchmark == benchmark_name:
                    self.after(0, self.loading_progress_bar.stop)
                    self.after(0, self.loading_progress_bar.grid_remove)
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
            line_colors = ["yellow", "cyan"]
        else:
            bar_color = "blue"
            line_colors = ["red", "green"]

        # Simulated FPS data
        benchmarks = ["Pyramid 5", "Sphere", "Tyre", "Water", "Muon Shower", "Water Pyramid"]
        fps_data = [85.3, 60.5, 72.8, 65.4, 90.1, 78.5]

        # Time series data for CPU/GPU usage
        time = np.arange(0, 100, 1)
        cpu_usage = np.sin(time / 10) * 10 + 50
        gpu_usage = np.cos(time / 10) * 10 + 50

        # Create new figure and axes
        self.fig, self.axs = plt.subplots(1, 2, figsize=(8, 4))

        # FPS Bar Graph
        self.axs[0].bar(benchmarks, fps_data, color=bar_color)
        self.axs[0].set_title("Average FPS per Benchmark")
        self.axs[0].set_ylabel("FPS")
        self.axs[0].set_ylim(0, 100)

        # CPU/GPU Usage Line Graph
        self.axs[1].plot(time, cpu_usage, label="CPU Usage", linestyle="--")
        self.axs[1].plot(time, gpu_usage, label="GPU Usage")
        self.axs[1].set_title("CPU and GPU Usage Over Time")
        self.axs[1].set_xlabel("Time (s)")
        self.axs[1].set_ylabel("Usage (%)")
        self.axs[1].legend()

        # Adjust colors based on appearance mode
        self.adjust_chart_mode()

        # Create a new canvas and display it
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tabview.tab("Results"))
        self.canvas.get_tk_widget().grid(row=0, column=0, padx=20, pady=(10, 0), sticky="nsew")
        self.canvas.draw()

        # Insert text results
        self.results_textbox.delete('1.0', tkinter.END)
        self.results_textbox.insert(tkinter.END, "Benchmark Results:\n\n- Pyramid 5: 85.3 FPS\n- Sphere: 60.5 FPS\n...")

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
            bar_color = "skyblue"
            line_colors = ["yellow", "cyan"]
        else:
            chart_bg_color = "#f0f0f0"
            text_color = "#202020"
            bar_color = "blue"
            line_colors = ["red", "green"]

        # Set face color of the figure
        self.fig.patch.set_facecolor(chart_bg_color)
        # Set face color of the axes and adjust text colors
        for ax in self.axs:
            ax.set_facecolor(chart_bg_color)
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.title.set_color(text_color)
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)

        # Update bar chart colors
        bars = self.axs[0].patches
        for bar in bars:
            bar.set_color(bar_color)

        # Update line chart colors
        lines = self.axs[1].get_lines()
        for line, color in zip(lines, line_colors):
            line.set_color(color)

        # Redraw the canvas to update the chart display
        if self.canvas is not None:
            self.canvas.draw()

    def view_results(self):
        self.display_results()

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
