import multiprocessing
import os
import threading
import tkinter
import tkinter.messagebox
import webbrowser

import _tkinter
import customtkinter
import matplotlib.pyplot as plt
import matplotlib.style as plot_style
from PIL import ImageFilter, Image
from customtkinter import CTkImage
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

        self.wm_iconbitmap('images/small_icon.ico')

        self.benchmark_manager = None  # Initialize as None
        self.benchmark_results = {}  # Store results for display
        self.stop_event = multiprocessing.Event()  # Event to signal stopping benchmarks
        self.image_area = None  # Placeholder for the image display area
        self.displayed_image = None  # To store the current image shown
        self.image_folder = "images"  # Folder where benchmark images are stored
        self.chart_bg_color = "#f0f0f0"  # Default chart background color

        # Configure window
        self.title("Fragment")
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

        # Sidebar Logo with Icon and Drop Shadow
        icon_image = Image.open(os.path.join(self.image_folder, 'large_icon.ico'))
        icon_with_shadow = self.add_drop_shadow(icon_image, shadow_offset=(5, 5), blur_radius=8)
        icon_ctkimage = CTkImage(icon_with_shadow, size=(64, 64))

        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="Fragment\nBenchmarking Tool",
            font=customtkinter.CTkFont(size=20, weight="bold"),
            image=icon_ctkimage,  # Add the image to the label
            compound="top",  # Display the image above the text
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
        self.about_button = customtkinter.CTkButton(
            self.sidebar_frame, text="About", command=self.show_about_info
        )
        self.about_button.grid(row=3, column=0, padx=20, pady=10)

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

        # Initialize scaling factor for results
        self.current_scaling = 1.0

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

        # Exit button aligned with the other buttons
        self.exit_button = customtkinter.CTkButton(
            self.sidebar_frame, text="Exit", command=self.exit_app
        )
        self.exit_button.grid(row=9, column=0, padx=20, pady=10)  # Align with other buttons

        # Create main content frame
        self.main_content_frame = customtkinter.CTkFrame(self)
        self.main_content_frame.grid(row=0, column=1, columnspan=4, rowspan=4, padx=(20, 20), pady=(20, 20),
                                     sticky="nsew")
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_propagate(True)  # Allow the frame to resize based on children

        # Tab view
        self.tabview = customtkinter.CTkTabview(self.main_content_frame, width=600)
        self.tabview.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.tabview.add("Settings")
        self.tabview.add("Scenarios")
        self.tabview.add("Results")

        # Results tab configuration to make the rows/columns resize dynamically
        self.tabview.tab("Results").grid_rowconfigure(0, weight=0)  # Textbox row
        self.tabview.tab("Results").grid_rowconfigure(1, weight=1)  # Results area row should resize
        self.tabview.tab("Results").grid_columnconfigure(0, weight=1)  # Allow the whole results area to expand
        self.tabview.tab("Results").grid_columnconfigure(1, weight=0)  # Column for scrollbar (if any)

        # Configure Settings and Scenarios tab grid for consistency
        common_padx = 30
        common_pady = (20, 10)

        # Settings tab grid layout
        self.tabview.tab("Settings").grid_columnconfigure((0, 1), weight=1)
        self.tabview.tab("Settings").grid_rowconfigure((0, 1, 2, 3), weight=1)

        # Settings tab elements
        self.resolution_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="Resolution:"
        )
        self.resolution_label.grid(row=0, column=0, padx=common_padx, pady=common_pady)
        self.resolution_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["640x480", "800x600", "1024x768", "1280x720", "1920x1080"],
        )
        self.resolution_optionmenu.grid(row=0, column=1, padx=common_padx, pady=common_pady)

        # Inside __init__ method in the Settings tab elements section
        self.msaa_level_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="MSAA Level:"
        )
        self.msaa_level_label.grid(row=1, column=0, padx=common_padx, pady=common_pady)
        self.msaa_level_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["0", "2", "4", "8"],  # Common MSAA levels (16x doesn't appear to be supported with OpenGL)
        )
        self.msaa_level_optionmenu.grid(row=1, column=1, padx=common_padx, pady=common_pady)
        self.msaa_level_optionmenu.set("0")  # Set default value to 0 (no MSAA)

        # Inside __init__ method in the Settings tab elements section
        self.particle_render_mode_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="Particle Render Mode:"
        )
        self.particle_render_mode_label.grid(row=2, column=0, padx=common_padx, pady=common_pady)
        self.particle_render_mode_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["CPU", "Transform Feedback", "Compute Shader"]
        )
        self.particle_render_mode_optionmenu.grid(row=2, column=1, padx=common_padx, pady=common_pady)
        self.particle_render_mode_optionmenu.set("CPU")  # Set default to "CPU"

        self.enable_vsync_checkbox = customtkinter.CTkCheckBox(
            self.tabview.tab("Settings"), text="Enable V-Sync"
        )
        self.enable_vsync_checkbox.grid(row=3, column=0, columnspan=2, padx=common_padx, pady=common_pady)

        # Scenarios tab grid layout for consistency
        self.tabview.tab("Scenarios").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Scenarios").grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        # Image area to display benchmark previews
        self.image_area = customtkinter.CTkLabel(self.tabview.tab("Scenarios"), text="")
        self.image_area.grid(row=0, column=1, padx=common_padx, pady=common_pady, rowspan=7, sticky="nsew")
        self.tabview.tab("Scenarios").grid_columnconfigure(1, weight=1)  # Ensure image area expands

        # Benchmark selection tab elements
        self.benchmark_list_label = customtkinter.CTkLabel(
            self.tabview.tab("Scenarios"), text="Select Benchmark Tests:"
        )
        self.benchmark_list_label.grid(row=0, column=0, padx=common_padx, pady=common_pady, sticky="w")

        # List of benchmarks
        self.benchmarks = [
            "Pyramid 5 - EMBM Test",
            "Sphere - Transparency Shader Test",
            "Tyre - Rubber Shader Test",
            "Water - Reflection Test",
            "Muon Shower - Particle System Test",
            "Water Pyramid - Mixed Test",
        ]

        self.currently_selected_benchmark_name = None

        # Dictionary to hold the state variables and checkboxes for each benchmark
        self.benchmark_vars = {}
        current_row = 1
        for benchmark in self.benchmarks:
            var = tkinter.BooleanVar(value=False)
            checkbox = customtkinter.CTkCheckBox(
                self.tabview.tab("Scenarios"), text=benchmark, variable=var
            )
            checkbox.grid(row=current_row, column=0, padx=common_padx, pady=(10, 10), sticky="w")

            # Bind <Enter> to display image when hovering over a checkbox
            checkbox.bind("<Enter>", lambda e, b=benchmark: self.display_image(b))

            # Store both the variable and the checkbox widget
            self.benchmark_vars[benchmark] = {'var': var, 'checkbox': checkbox}
            current_row += 1

        # 'Select All' and 'Deselect All' buttons
        self.select_all_button = customtkinter.CTkButton(
            self.tabview.tab("Scenarios"), text="Select All", command=self.select_all_benchmarks
        )
        self.select_all_button.grid(row=current_row, column=0, padx=common_padx, pady=(20, 10), sticky="w")
        current_row += 1

        self.deselect_all_button = customtkinter.CTkButton(
            self.tabview.tab("Scenarios"), text="Deselect All", command=self.deselect_all_benchmarks
        )
        self.deselect_all_button.grid(row=current_row, column=0, padx=common_padx, pady=(10, 20), sticky="w")

        # Results tab with scrollable area
        # Create a frame for the results_textbox
        self.results_textbox_frame = customtkinter.CTkFrame(self.tabview.tab("Results"))
        self.results_textbox_frame.grid(row=0, column=0, sticky="nsew")
        self.results_textbox_frame.grid_columnconfigure(0, weight=1)

        # Initialize results_textbox inside results_textbox_frame with smaller font
        self.results_textbox = customtkinter.CTkTextbox(
            self.results_textbox_frame, width=400, height=100,
            font=customtkinter.CTkFont(size=10)
        )
        self.results_textbox.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="nsew")

        # Replace Canvas and Scrollbar with CTkScrollableFrame
        self.results_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Results"))
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Set default values
        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")
        self.resolution_optionmenu.set("1024x768")
        self.msaa_level_optionmenu.set("0")
        self.particle_render_mode_optionmenu.set("Transform Feedback")
        self.enable_vsync_checkbox.select()

        # Prepare the graph canvas for results
        self.fig = None  # Will be created in display_results
        self.axs = None
        self.canvas = None

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Loading progress bar at the bottom of the right side panel
        self.loading_progress_bar = customtkinter.CTkProgressBar(self, mode="indeterminate")
        self.loading_progress_bar.grid(row=4, column=1, columnspan=4, padx=(20, 20), pady=(0, 10), sticky="ew")
        self.loading_progress_bar.grid_remove()  # Hide it initially

        # Bind the window resize event
        self.bind("<Configure>", self.on_window_resize)

    def update_results_background(self):
        # Get the current background color based on the theme
        bg_color_list = customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"]

        # Determine the correct color based on the current appearance mode
        if customtkinter.get_appearance_mode() == "Dark":
            bg_color = bg_color_list[1]  # Dark mode color
        else:
            bg_color = bg_color_list[0]  # Light mode color

        # Set the background color of the frames
        self.results_frame.configure(fg_color=bg_color)
        self.results_textbox_frame.configure(fg_color=bg_color)
        self.results_textbox.configure(bg_color=bg_color)

    def display_image(self, benchmark_name):
        self.currently_selected_benchmark_name = benchmark_name

        # Construct the path to the image file
        image_path = os.path.join(self.image_folder, f"{benchmark_name}.png")

        if os.path.exists(image_path):
            img = Image.open(image_path)

            # Add a drop shadow to the image
            img_with_shadow = self.add_drop_shadow(img)

            # Get the original dimensions of the image with shadow
            img_original_width, img_original_height = img_with_shadow.width, img_with_shadow.height

            # Get the current window size
            window_width = self.winfo_width()
            window_height = self.winfo_height()

            # Calculate the available width and height for the image
            available_width = int(window_width * 0.4)
            available_height = int(window_height * 0.5)

            # Calculate the scale factor to maintain aspect ratio
            width_scale = available_width / img_original_width
            height_scale = available_height / img_original_height
            scale_factor = min(width_scale, height_scale)

            # Scale the image dimensions while maintaining aspect ratio
            image_area_width = int(img_original_width * scale_factor)
            image_area_height = int(img_original_height * scale_factor)

            # Resize the image with shadow based on the calculated dimensions
            img_resized = img_with_shadow.resize((image_area_width, image_area_height), Image.LANCZOS)
            self.displayed_image = CTkImage(light_image=img_resized, dark_image=img_resized,
                                            size=(image_area_width, image_area_height))

            # Apply the resized image with shadow and set the area size
            self.image_area.configure(image=self.displayed_image, width=image_area_width, height=image_area_height)

            # Keep a reference to prevent garbage collection
            self.image_area.image = self.displayed_image
        else:
            self.image_area.configure(image=None)  # Clear if no image found

    def add_drop_shadow(self, image, shadow_offset=(10, 10), shadow_color=(0, 0, 0), blur_radius=10,
                        shadow_opacity=100):
        # Create a shadow image (black with opacity)
        shadow = Image.new("RGBA", (image.width + shadow_offset[0], image.height + shadow_offset[1]),
                           color=(0, 0, 0, 0))

        # Create a shadow shape that matches the original image
        shadow_image = Image.new("RGBA", image.size, color=shadow_color + (shadow_opacity,))

        # Paste the shadow on the shadow canvas with an offset
        shadow.paste(shadow_image, (shadow_offset[0], shadow_offset[1]))

        # Apply a blur to the shadow to create the drop shadow effect
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))

        # Create a base canvas to combine shadow and image
        combined = Image.new("RGBA", shadow.size)
        combined.paste(shadow, (0, 0), shadow)  # Paste shadow
        combined.paste(image, (0, 0), image)  # Paste original image on top of shadow

        return combined

    def on_window_resize(self, event=None):
        # Cancel any previous scheduled resizing for the image
        if hasattr(self, '_image_resize_after_id'):
            self.after_cancel(self._image_resize_after_id)

        # Schedule a new image resize to happen after 200 ms (or any delay you prefer)
        self._image_resize_after_id = self.after(200, self.resize_image_after_window_resize)

        # Cancel any previous scheduled resizing for the canvas
        if hasattr(self, '_canvas_resize_after_id'):
            self.after_cancel(self._canvas_resize_after_id)

        # Schedule a new canvas resize to happen after 200 ms (or any delay you prefer)
        self._canvas_resize_after_id = self.after(200, self._resize_canvas)

    def resize_image_after_window_resize(self):
        # Logic for resizing the image after the window resize
        if self.currently_selected_benchmark_name:
            self.display_image(self.currently_selected_benchmark_name)

    def select_all_benchmarks(self):
        for item in self.benchmark_vars.values():
            item['var'].set(True)

    def deselect_all_benchmarks(self):
        for item in self.benchmark_vars.values():
            item['var'].set(False)

    def disable_widgets(self):
        # Disable sidebar buttons
        self.benchmark_button.configure(state="disabled")
        self.demo_button.configure(state="disabled")
        self.about_button.configure(state="disabled")
        # Disable tab buttons (disable tab switching)
        self.tabview._segmented_button.configure(state="disabled")
        # Disable option menus
        self.resolution_optionmenu.configure(state="disabled")
        self.msaa_level_optionmenu.configure(state="disabled")
        self.particle_render_mode_optionmenu.configure(state="disabled")
        # Disable checkboxes
        self.enable_vsync_checkbox.configure(state="disabled")
        for item in self.benchmark_vars.values():
            item['checkbox'].configure(state="disabled")
        # Disable 'Select All' and 'Deselect All' buttons
        self.select_all_button.configure(state="disabled")
        self.deselect_all_button.configure(state="disabled")

    def enable_widgets(self):
        # Enable sidebar buttons
        self.benchmark_button.configure(state="normal")
        self.demo_button.configure(state="normal")
        self.about_button.configure(state="normal")
        # Enable tab buttons (enable tab switching)
        self.tabview._segmented_button.configure(state="normal")
        # Enable option menus
        self.resolution_optionmenu.configure(state="normal")
        self.msaa_level_optionmenu.configure(state="normal")
        self.particle_render_mode_optionmenu.configure(state="normal")
        # Enable checkboxes
        self.enable_vsync_checkbox.configure(state="normal")
        for item in self.benchmark_vars.values():
            item['checkbox'].configure(state="normal")
        # Enable 'Select All' and 'Deselect All' buttons
        self.select_all_button.configure(state="normal")
        self.deselect_all_button.configure(state="normal")

    def run_benchmark(self):
        # Get selected benchmarks from the checkboxes
        selected_benchmarks = [
            benchmark for benchmark, item in self.benchmark_vars.items() if item['var'].get()
        ]
        if not selected_benchmarks:
            tkinter.messagebox.showwarning("No Selection", "Please select at least one benchmark.")
            return

        # Retrieve the selected resolution from the GUI
        resolution_str = self.resolution_optionmenu.get()
        width, height = map(int, resolution_str.split('x'))  # Convert "1024x768" to (1024, 768)

        # Retrieve the selected MSAA level from the GUI
        msaa_level = int(self.msaa_level_optionmenu.get())

        # Retrieve the selected particle render mode from the GUI
        particle_render_mode = self.particle_render_mode_optionmenu.get().lower().replace(" ", "_")

        # Map benchmark names to functions
        benchmark_functions = {
            "Pyramid 5 - EMBM Test": run_pyramid_benchmark,
            "Sphere - Transparency Shader Test": run_sphere_benchmark,
            "Tyre - Rubber Shader Test": run_tyre_benchmark,
            "Water - Reflection Test": run_water_benchmark,
            "Muon Shower - Particle System Test": run_muon_shower_benchmark,
            "Water Pyramid - Mixed Test": run_water_pyramid_benchmark,
        }

        # Clear previous results
        self.benchmark_results = {}
        self.benchmark_manager = BenchmarkManager(self.stop_event)  # Pass stop_event here

        for benchmark_name in selected_benchmarks:
            if benchmark_name in benchmark_functions:
                # Pass the resolution, MSAA level, and particle render mode to the benchmark manager
                self.benchmark_manager.add_benchmark(
                    benchmark_name,
                    benchmark_functions[benchmark_name],
                    (width, height),
                    msaa_level=msaa_level,
                    particle_render_mode=particle_render_mode,
                )
            else:
                tkinter.messagebox.showerror("Error", f"No benchmark found for {benchmark_name}")

        # Disable widgets
        self.disable_widgets()

        # Show the loading bar
        self.show_loading_bar()

        # Run benchmarks in a separate thread to keep GUI responsive
        threading.Thread(target=self.run_benchmarks_thread, daemon=True).start()

    def run_benchmarks_thread(self):
        self.benchmark_manager.run_benchmarks()
        # Hide the loading bar
        self.after(0, self.hide_loading_bar)
        if self.benchmark_manager.benchmark_stopped_by_user:
            # Benchmark was stopped by user
            self.after(0, lambda: tkinter.messagebox.showinfo("Benchmark Stopped", "Benchmark stopped by user."))
        else:
            # Store results
            self.benchmark_results = self.benchmark_manager.get_results()
            # Display results
            self.after(0, self.generate_and_display_results)
            # Switch to the "Results" tab
            self.after(0, lambda: self.tabview.set("Results"))
        # Re-enable widgets
        self.after(0, self.enable_widgets)

    def demo_mode(self):
        # If demo mode runs a process, similar disabling and enabling of widgets would be applied here
        tkinter.messagebox.showinfo("Demo Mode", "Demo mode started...")

    def show_loading_bar(self):
        self.loading_progress_bar.grid()
        self.loading_progress_bar.start()

    def hide_loading_bar(self):
        self.loading_progress_bar.stop()
        self.loading_progress_bar.grid_remove()

    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def show_about_info(self):
        about_window = customtkinter.CTkToplevel(self)
        about_window.iconbitmap('images/small_icon.ico')
        about_window.title("About")
        about_window.geometry("400x250")
        about_window.resizable(False, False)

        # Center the window over the parent window
        self.center_window(about_window)

        # Ensure the window opens over the top of the main window
        about_window.transient(self)
        about_window.lift()
        about_window.focus_force()
        about_window.grab_set()

        # Load the large icon image with drop shadow
        icon_image = Image.open(os.path.join(self.image_folder, 'large_icon.ico'))
        icon_with_shadow = self.add_drop_shadow(icon_image, shadow_offset=(5, 5), blur_radius=8)
        icon_ctkimage = CTkImage(icon_with_shadow, size=(64, 64))

        # Create the label with both icon and title
        title_label = customtkinter.CTkLabel(
            about_window,
            text="Fragment",
            font=("Arial", 16, "bold"),
            image=icon_ctkimage,  # Add the icon to the label
            compound="top",  # Display the icon above the text
        )
        title_label.pack(pady=(10, 5))

        version_label = customtkinter.CTkLabel(about_window, text="Version 1.0", font=("Arial", 12))
        version_label.pack(pady=(0, 5))

        developed_label = customtkinter.CTkLabel(about_window, text="Developed by 314reactor", font=("Arial", 12))
        developed_label.pack(pady=(0, 10))

        # Links
        links = [
            ("GitHub", "https://github.com/LordofBone"),
            ("Hackster.io", "https://www.hackster.io/314reactor"),
            ("Electromaker.io", "https://www.electromaker.io/profile/314Reactor"),
        ]

        for name, url in links:
            link_label = customtkinter.CTkLabel(
                about_window, text=name, font=("Arial", 12), text_color="blue", cursor="hand2"
            )
            link_label.pack()
            link_label.bind("<Button-1>", lambda e, url=url: webbrowser.open_new(url))

        # Close button
        close_button = customtkinter.CTkButton(about_window, text="Close", command=about_window.destroy)
        close_button.pack(pady=(10, 10))

        about_window.after(250, lambda: about_window.iconbitmap('images/small_icon.ico'))

    def generate_and_display_results(self):
        # Destroy the current results frame to reset the scroll position
        self.results_frame.destroy()

        # Recreate the results frame with the same configurations
        self.results_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Results"))
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Continue with displaying the results
        self.after(0, self.display_results)
        # Switch to the "Results" tab
        self.after(0, lambda: self.tabview.set("Results"))

    def display_results(self):
        plot_style.use('mpl20')  # Use default style

        # Clear previous canvas and figure if they exist
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None

        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None

        # Determine colors based on current mode
        current_mode = customtkinter.get_appearance_mode()
        if current_mode == "Dark":
            bar_color = "skyblue"
            line_colors = ["yellow", "cyan", "magenta"]
        else:
            bar_color = "blue"
            line_colors = ["red", "green", "purple"]

        # Check if there are benchmark results
        if not self.benchmark_results:
            for widget in self.results_frame.winfo_children():
                widget.destroy()
            return

        num_benchmarks = len(self.benchmark_results)
        fig_height = 4 * num_benchmarks * self.current_scaling  # Apply scaling factor
        fig_width = 11 * self.current_scaling  # Apply scaling factor

        # Create figure and axes with transparent background
        self.fig, self.axs = plt.subplots(
            num_benchmarks, 2,
            figsize=(fig_width, fig_height),
            squeeze=False,
            constrained_layout=True,
            facecolor='none'
        )

        self.chart_set_font_size()

        # Update results textbox
        self.results_textbox.delete('1.0', tkinter.END)
        self.results_textbox.insert(tkinter.END, "Benchmark Results:\n\n")

        for idx, (benchmark_name, data) in enumerate(self.benchmark_results.items()):
            fps_data = data['fps_data']
            cpu_usage_data = data['cpu_usage_data']
            gpu_usage_data = data['gpu_usage_data']
            elapsed_time = data['elapsed_time']

            # Generate the time axis based on the actual elapsed time
            if elapsed_time > 0 and len(fps_data) > 0:
                interval = elapsed_time / len(fps_data)
                time_data = [i * interval for i in range(len(fps_data))]
            else:
                time_data = range(len(fps_data))

            # FPS Line Graph
            self.axs[idx, 0].plot(time_data, fps_data, color=bar_color)
            self.axs[idx, 0].set_title(f"FPS Over Time - {benchmark_name}")
            self.axs[idx, 0].set_xlabel("Time (s)")
            self.axs[idx, 0].set_ylabel("FPS")

            # CPU/GPU Usage Line Graph
            self.axs[idx, 1].plot(
                time_data, cpu_usage_data,
                label="CPU Usage", linestyle="--", color=line_colors[0]
            )
            self.axs[idx, 1].plot(
                time_data, gpu_usage_data,
                label="GPU Usage", color=line_colors[1]
            )
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
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.results_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew", padx=20, pady=(5, 10))

        # Ensure the canvas expands with the frame
        self.results_frame.grid_rowconfigure(0, weight=1)
        self.results_frame.grid_columnconfigure(0, weight=1)

        self.results_frame.configure(fg_color=self.chart_bg_color)

        self.canvas.draw_idle()

    def on_canvas_resize(self, event):
        if hasattr(self, '_canvas_resize_after_id'):
            self.after_cancel(self._canvas_resize_after_id)
        self._canvas_resize_after_id = self.after(200, self._resize_canvas)

    def _resize_canvas(self):
        if self.canvas is not None and self.fig is not None:
            width = self.canvas.get_tk_widget().winfo_width()
            height = self.canvas.get_tk_widget().winfo_height()

            if width <= 0 or height <= 0:
                return

            dpi = self.fig.get_dpi()
            fig_width = width / dpi
            fig_height = height / dpi

            self.fig.set_size_inches(fig_width, fig_height, forward=True)
            self.canvas.draw_idle()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)
        self.adjust_chart_mode()
        self.update_results_background()  # Update the background colors

    def change_scaling_event(self, new_scaling: str):
        # Parse new scaling factor
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

        # Store the new scaling factor
        self.current_scaling = new_scaling_float

        # Update the chart size based on the new scaling factor
        self.update_chart_scaling()

    def chart_set_font_size(self):
        # Recalculate the figure size based on the scaling factor
        num_benchmarks = len(self.benchmark_results)
        fig_height = 4 * num_benchmarks * self.current_scaling  # Scale height accordingly
        fig_width = 11 * self.current_scaling  # Scale width accordingly

        # Set new figure size
        self.fig.set_size_inches(fig_width, fig_height, forward=True)

        # Update font sizes dynamically
        plt.rcParams.update({
            'font.size': int(10 * self.current_scaling),
            'axes.titlesize': int(12 * self.current_scaling),
            'axes.labelsize': int(11 * self.current_scaling),
            'xtick.labelsize': int(10 * self.current_scaling),
            'ytick.labelsize': int(10 * self.current_scaling),
            'legend.fontsize': int(10 * self.current_scaling),
        })

    def update_chart_scaling(self):
        if self.fig is not None and self.canvas is not None:
            self.chart_set_font_size()

            # Apply new font sizes to the existing axes
            for ax in self.axs.flatten():
                ax.title.set_fontsize(int(12 * self.current_scaling))
                ax.xaxis.label.set_fontsize(int(11 * self.current_scaling))
                ax.yaxis.label.set_fontsize(int(11 * self.current_scaling))
                ax.tick_params(axis='both', labelsize=int(10 * self.current_scaling))
                legend = ax.get_legend()
                if legend is not None:
                    for text in legend.get_texts():
                        text.set_fontsize(int(10 * self.current_scaling))

            # Redraw the canvas with the updated sizes
            self.canvas.draw_idle()

    def adjust_chart_mode(self):
        # Get the effective appearance mode
        mode = customtkinter.get_appearance_mode()

        if not hasattr(self, 'fig') or not hasattr(self, 'axs') or self.fig is None or self.axs is None:
            return

        if mode == "Dark":
            self.chart_bg_color = "#2c2c2c"
            text_color = "#b0b0b0"
        else:
            self.chart_bg_color = "#f0f0f0"
            text_color = "#202020"

        # Set the face color of the figure and canvas background to match
        self.fig.patch.set_facecolor(self.chart_bg_color)
        self.fig.patch.set_edgecolor(self.chart_bg_color)

        # Update axes and text colors
        for ax in self.axs.flatten():
            ax.set_facecolor(self.chart_bg_color)
            ax.tick_params(axis='x', colors=text_color)
            ax.tick_params(axis='y', colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            ax.title.set_color(text_color)

            # Set spines' edge color
            for spine in ax.spines.values():
                spine.set_edgecolor(text_color)

            # Remove grid lines if desired
            ax.grid(False)

        # Redraw the canvas
        if self.canvas is not None:
            self.canvas.draw_idle()

    def exit_app(self):
        try:
            # Cancel any pending resize operation
            if hasattr(self, '_resize_after_id'):
                self.after_cancel(self._resize_after_id)

            # Signal benchmarks to stop
            self.stop_event.set()

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
        finally:
            # Force exit the application
            os._exit(0)
