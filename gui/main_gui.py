import io
import multiprocessing
import os
import platform
import threading
import tkinter
import tkinter.messagebox
import webbrowser

import GPUtil
import _tkinter
import customtkinter
import matplotlib.pyplot as plt
import matplotlib.style as plot_style
import numpy as np
import psutil
import pygame
from PIL import Image, ImageFilter, ImageTk
from customtkinter import CTkImage
from scipy.interpolate import make_interp_spline

from benchmarks.baryon import run_benchmark as run_particle_benchmark
from benchmarks.eidolon import run_benchmark as run_sphere_benchmark
from benchmarks.gelidus import run_benchmark as run_water_benchmark
from benchmarks.shimmer import run_benchmark as run_water_pyramid_benchmark
from benchmarks.treadlock import run_benchmark as run_tyre_benchmark
from benchmarks.ætherial import run_benchmark as run_pyramid_benchmark
from components.benchmark_manager import BenchmarkManager
from config.path_config import images_dir, themes_dir
from version import __version__

customtkinter.set_appearance_mode("System")  # Modes: "System", "Dark", "Light"
customtkinter.set_default_color_theme(os.path.join(themes_dir, "314reactor.json"))

# Centralized Benchmark Names and Functions
BENCHMARKS = {
    "Ætherial - EMBM Test": run_pyramid_benchmark,
    "Eidolon - Transparency Shader Test": run_sphere_benchmark,
    "Treadlock - Parallax Shader Test": run_tyre_benchmark,
    "Gelidus - Reflection Test": run_water_benchmark,
    "Baryon - Particle System Test": run_particle_benchmark,
}


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # Initialize Demo Mode flag
        self.is_demo_mode = False

        # Retrieve the desktop resolution
        pygame.init()
        self.desktop_info = pygame.display.Info()

        self.benchmark_manager = None  # Initialize as None
        self.benchmark_results = {}  # Store results for display
        self.stop_event = multiprocessing.Event()  # Event to signal stopping benchmarks
        self.image_area = None  # Placeholder for the image display area
        self.displayed_image = None  # To store the current image shown
        self.image_folder = images_dir  # Folder where benchmark images are stored
        self.chart_bg_color = "#f0f0f0"  # Default chart background color
        self.chart_text_color = "#202020"  # Default chart text color

        # Set the window icon
        try:
            self.wm_iconbitmap(os.path.join(self.image_folder, "small_icon.ico"))
        except _tkinter.TclError:
            print("Icon file not found or running on an OS that doesn't support this. Skipping.")

        # Configure window
        self.title("Fragment")
        self.geometry(f"{1200}x700")

        # Configure grid layout (6 rows, 5 columns)
        self.grid_columnconfigure(0, weight=0)  # Sidebar column
        self.grid_columnconfigure((1, 2, 3, 4), weight=1)  # Main content columns
        self.grid_rowconfigure((0, 1, 2, 3), weight=1)  # Main content rows
        self.grid_rowconfigure(4, minsize=25)  # For loading bar
        self.grid_rowconfigure(5, weight=0)  # For system specs frame

        # Create sidebar frame with widgets
        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=6, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Sidebar Logo with Icon and Drop Shadow
        icon_image = Image.open(os.path.join(self.image_folder, "large_icon.ico"))
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

        self.demo_button = customtkinter.CTkButton(self.sidebar_frame, text="Shimmer (Demo)", command=self.demo_mode)
        self.demo_button.grid(row=2, column=0, padx=20, pady=10)

        # Bind hover events to the demo button
        self.demo_button.bind("<Enter>", self.on_demo_hover)
        self.demo_button.bind("<Leave>", self.on_demo_leave)

        self.about_button = customtkinter.CTkButton(self.sidebar_frame, text="About", command=self.show_about_info)
        self.about_button.grid(row=3, column=0, padx=20, pady=10)

        # Appearance mode option menu
        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["Dark", "Light"],
            command=self.change_appearance_mode_event,
        )
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        # Initialize scaling factor for results
        self.current_scaling = 1.0

        # UI scaling option menu
        self.scaling_label = customtkinter.CTkLabel(self.sidebar_frame, text="UI Scaling:", anchor="w")
        self.scaling_label.grid(row=7, column=0, padx=20, pady=(10, 0))
        self.scaling_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["80%", "90%", "100%", "110%", "120%"],
            command=self.change_scaling_event,
        )
        self.scaling_optionemenu.grid(row=8, column=0, padx=20, pady=(10, 20))

        # Exit button aligned with the other buttons
        self.exit_button = customtkinter.CTkButton(self.sidebar_frame, text="Exit", command=self.exit_app)
        self.exit_button.grid(row=9, column=0, padx=20, pady=10)  # Align with other buttons

        # Create main content frame
        self.main_content_frame = customtkinter.CTkFrame(self)
        self.main_content_frame.grid(
            row=0, column=1, columnspan=4, rowspan=4, padx=(20, 20), pady=(20, 20), sticky="nsew"
        )
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
        self.tabview.tab("Results").grid_rowconfigure(2, weight=0)  # Performance score label
        self.tabview.tab("Results").grid_columnconfigure(0, weight=1)  # Allow the whole results area to expand
        self.tabview.tab("Results").grid_columnconfigure(1, weight=0)  # Column for scrollbar (if any)

        # Configure Settings and Scenarios tab grid for consistency
        common_padx = 30
        common_pady = (20, 10)

        # Settings tab grid layout (adjusted row numbers)
        self.tabview.tab("Settings").grid_columnconfigure((0, 1), weight=1)
        self.tabview.tab("Settings").grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

        # Row 0: Resolution remains unchanged
        self.resolution_label = customtkinter.CTkLabel(self.tabview.tab("Settings"), text="Resolution:")
        self.resolution_label.grid(row=0, column=0, padx=common_padx, pady=common_pady)
        self.resolution_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["640x480", "800x600", "1024x768", "1280x720", "1920x1080", "Fullscreen"],
        )
        self.resolution_optionmenu.grid(row=0, column=1, padx=common_padx, pady=common_pady)

        # Row 1: MSAA Level
        self.msaa_level_label = customtkinter.CTkLabel(self.tabview.tab("Settings"), text="MSAA Level:")
        self.msaa_level_label.grid(row=1, column=0, padx=common_padx, pady=common_pady)
        self.msaa_level_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["0", "2", "4", "8"],  # Common MSAA levels
        )
        self.msaa_level_optionmenu.grid(row=1, column=1, padx=common_padx, pady=common_pady)
        self.msaa_level_optionmenu.set("4")  # Set default

        # Row 2: Anisotropic Filtering
        self.anisotropy_label = customtkinter.CTkLabel(self.tabview.tab("Settings"), text="Anisotropy Level:")
        self.anisotropy_label.grid(row=2, column=0, padx=common_padx, pady=common_pady)
        self.anisotropy_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["1", "2", "4", "8", "16"],
        )
        self.anisotropy_optionmenu.grid(row=2, column=1, padx=common_padx, pady=common_pady)

        # Row 3: NEW – Shading Model dropdown
        self.shading_model_label = customtkinter.CTkLabel(self.tabview.tab("Settings"), text="Shading Model:")
        self.shading_model_label.grid(row=3, column=0, padx=common_padx, pady=common_pady)
        self.shading_model_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["Diffuse", "Phong", "PBR"],
        )
        self.shading_model_optionmenu.grid(row=3, column=1, padx=common_padx, pady=common_pady)

        # Row 4: Update Shadow Quality (shifted down from row 3)
        self.shadow_quality_label = customtkinter.CTkLabel(self.tabview.tab("Settings"), text="Shadow Quality:")
        self.shadow_quality_label.grid(row=4, column=0, padx=common_padx, pady=common_pady)
        self.shadow_quality_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"),
            values=["None", "1024x1024", "2048x2048", "4096x4096"],
        )
        self.shadow_quality_optionmenu.grid(row=4, column=1, padx=common_padx, pady=common_pady)

        # Row 5: Update Particle Render Mode (shifted down from row 4)
        self.particle_render_mode_label = customtkinter.CTkLabel(
            self.tabview.tab("Settings"), text="Particle Render Mode:"
        )
        self.particle_render_mode_label.grid(row=5, column=0, padx=common_padx, pady=common_pady)
        self.particle_render_mode_optionmenu = customtkinter.CTkOptionMenu(
            self.tabview.tab("Settings"), values=["CPU", "Transform Feedback", "Compute Shader"]
        )
        self.particle_render_mode_optionmenu.grid(row=5, column=1, padx=common_padx, pady=common_pady)

        # Row 6: Update V-Sync and Sound (shifted down from row 5)
        self.enable_vsync_checkbox = customtkinter.CTkCheckBox(self.tabview.tab("Settings"), text="Enable V-Sync")
        self.enable_vsync_checkbox.grid(row=6, column=0, columnspan=1, padx=common_padx, pady=common_pady)
        self.sound_enabled_checkbox = customtkinter.CTkCheckBox(self.tabview.tab("Settings"), text="Enable Sound")
        self.sound_enabled_checkbox.grid(row=6, column=1, columnspan=1, padx=common_padx, pady=common_pady)

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
        self.benchmarks = list(BENCHMARKS.keys())

        self.currently_selected_benchmark_name = None

        # Dictionary to hold the state variables and checkboxes for each benchmark
        self.benchmark_vars = {}
        current_row = 1
        for benchmark in self.benchmarks:
            var = tkinter.BooleanVar(value=False)
            checkbox = customtkinter.CTkCheckBox(self.tabview.tab("Scenarios"), text=benchmark, variable=var)
            checkbox.grid(row=current_row, column=0, padx=common_padx, pady=(10, 10), sticky="w")

            # Bind <Enter> to display image when hovering over a checkbox
            checkbox.bind("<Enter>", lambda e, b=benchmark: self.display_image(b))

            # Store both the variable and the checkbox widget
            self.benchmark_vars[benchmark] = {"var": var, "checkbox": checkbox}
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
            self.results_textbox_frame, width=400, height=100, font=customtkinter.CTkFont(size=10)
        )
        self.results_textbox.pack(anchor="center", fill="both", expand=True)

        # Label to display the performance score
        self.performance_score_label = customtkinter.CTkLabel(
            self.tabview.tab("Results"), text="", font=customtkinter.CTkFont(size=14, weight="bold")
        )
        self.performance_score_label.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="nsew")

        # Replace Canvas and Scrollbar with CTkScrollableFrame
        self.results_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Results"))
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Set default values
        self.appearance_mode_optionemenu.set("Dark")
        self.scaling_optionemenu.set("100%")
        self.resolution_optionmenu.set("1024x768")
        self.msaa_level_optionmenu.set("4")
        self.anisotropy_optionmenu.set("16")
        self.shading_model_optionmenu.set("PBR")
        self.shadow_quality_optionmenu.set("2048x2048")
        self.particle_render_mode_optionmenu.set("Transform Feedback")
        self.sound_enabled_checkbox.select()

        # Prepare the graph canvas for results
        self.fig = None  # Will be created in display_results
        self.axs = None

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Loading progress bar at the bottom of the right side panel
        self.loading_progress_bar = customtkinter.CTkProgressBar(self, mode="indeterminate")
        self.loading_progress_bar.grid(row=4, column=1, columnspan=4, padx=(20, 20), pady=(0, 10), sticky="ew")
        self.loading_progress_bar.grid_remove()  # Hide it initially

        # System Specs Frame at the bottom center
        self.system_specs_frame = customtkinter.CTkFrame(self)
        self.system_specs_frame.grid(row=5, column=1, columnspan=4, padx=(20, 20), pady=(0, 10), sticky="ew")
        self.system_specs_frame.grid_columnconfigure(0, weight=1)

        # Retrieve system specs
        cpu_info = self.get_cpu_info()
        gpu_info = self.get_gpu_info()
        ram_info = self.get_ram_info()

        # Create the label to display the system specs
        self.system_specs_label = customtkinter.CTkLabel(
            self.system_specs_frame,
            text=f"CPU: {cpu_info}     GPU: {gpu_info}     RAM: {ram_info}",
            font=customtkinter.CTkFont(size=12),
        )
        self.system_specs_label.grid(row=0, column=0, padx=20, pady=5, sticky="ew")
        self.system_specs_label.configure(anchor="center")  # Center the text

        # Variables to manage resizing
        self.is_resizing = False
        self.resize_after_id = None

        self.shadow_quality_mapping = {
            "None": 0,
            "1024x1024": 1024,
            "2048x2048": 2048,
            "4096x4096": 4096,
        }

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
        # Replace any characters that are invalid in file names if necessary
        sanitized_name = benchmark_name.replace(":", "").replace("/", "").replace("\\", "")
        image_path = os.path.join(self.image_folder, f"{sanitized_name}.png")

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
            self.displayed_image = CTkImage(
                light_image=img_resized, dark_image=img_resized, size=(image_area_width, image_area_height)
            )

            # Apply the resized image with shadow and set the area size
            self.image_area.configure(image=self.displayed_image, width=image_area_width, height=image_area_height)

            # Keep a reference to prevent garbage collection
            self.image_area.image = self.displayed_image
        else:
            self.image_area.configure(image=None)  # Clear if no image found

    def display_demo_image(self):
        benchmark_name = "Shimmer (Demo)"
        self.currently_selected_benchmark_name = benchmark_name

        # Construct the path to the demo image file
        sanitized_name = benchmark_name.replace(":", "").replace("/", "").replace("\\", "")
        image_path = os.path.join(self.image_folder, f"{sanitized_name}.png")

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
            self.displayed_image = CTkImage(
                light_image=img_resized, dark_image=img_resized, size=(image_area_width, image_area_height)
            )

            # Apply the resized image with shadow and set the area size
            self.image_area.configure(image=self.displayed_image, width=image_area_width, height=image_area_height)

            # Keep a reference to prevent garbage collection
            self.image_area.image = self.displayed_image
        else:
            self.image_area.configure(image=None)  # Clear if no image found

    def add_drop_shadow(self, image, shadow_offset=(10, 35), shadow_color=(0, 0, 0), blur_radius=5, shadow_opacity=100):
        # Create a shadow image (black with opacity)
        shadow = Image.new(
            "RGBA", (image.width + shadow_offset[0], image.height + shadow_offset[1]), color=(0, 0, 0, 0)
        )

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

    def get_cpu_info(self):
        cpu_brand = platform.processor()
        if not cpu_brand:
            cpu_brand = platform.machine()
        cpu_count = psutil.cpu_count(logical=True)
        return f"{cpu_brand} ({cpu_count} cores)"

    def get_gpu_info(self):
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]  # Get the first GPU
            return f"{gpu.name} (Driver {gpu.driver})"
        else:
            return "No GPU Found"

    def get_ram_info(self):
        ram_bytes = psutil.virtual_memory().total
        ram_gb = ram_bytes / (1024**3)  # Convert bytes to GB
        return f"{ram_gb:.1f} GB"

    def on_resize_complete(self):
        # Re-render the chart to fit within the resized window
        if self.benchmark_results:
            self.display_results()
        self.is_resizing = False  # Reset the resizing flag

    def select_all_benchmarks(self):
        for item in self.benchmark_vars.values():
            item["var"].set(True)

    def deselect_all_benchmarks(self):
        for item in self.benchmark_vars.values():
            item["var"].set(False)

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
        self.anisotropy_optionmenu.configure(state="disabled")
        self.shading_model_optionmenu.configure(state="disabled")
        self.shadow_quality_optionmenu.configure(state="disabled")
        self.particle_render_mode_optionmenu.configure(state="disabled")
        # Disable checkboxes
        self.enable_vsync_checkbox.configure(state="disabled")
        self.sound_enabled_checkbox.configure(state="disabled")
        for item in self.benchmark_vars.values():
            item["checkbox"].configure(state="disabled")
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
        self.anisotropy_optionmenu.configure(state="normal")
        self.shading_model_optionmenu.configure(state="normal")
        self.shadow_quality_optionmenu.configure(state="normal")
        self.particle_render_mode_optionmenu.configure(state="normal")
        # Enable checkboxes
        self.enable_vsync_checkbox.configure(state="normal")
        self.sound_enabled_checkbox.configure(state="normal")
        for item in self.benchmark_vars.values():
            item["checkbox"].configure(state="normal")
        # Enable 'Select All' and 'Deselect All' buttons
        self.select_all_button.configure(state="normal")
        self.deselect_all_button.configure(state="normal")

    def run_benchmark(self):
        # Get selected benchmarks from the checkboxes
        selected_benchmarks = [benchmark for benchmark, item in self.benchmark_vars.items() if item["var"].get()]
        if not selected_benchmarks:
            tkinter.messagebox.showwarning("No Selection", "Please select at least one benchmark.")
            return

        # Retrieve the selected resolution from the GUI
        resolution_str = self.resolution_optionmenu.get()
        if resolution_str == "Fullscreen":
            width, height = self.desktop_info.current_w, self.desktop_info.current_h
            fullscreen = True
        else:
            width, height = map(int, resolution_str.split("x"))
            fullscreen = False

        # Retrieve other settings from the GUI
        msaa_level = int(self.msaa_level_optionmenu.get())
        anisotropy = int(self.anisotropy_optionmenu.get())

        # NEW: Retrieve the selected shading model
        shading_model = self.shading_model_optionmenu.get().lower()

        shadow_quality_str = self.shadow_quality_optionmenu.get()
        shadow_map_resolution = self.shadow_quality_mapping.get(shadow_quality_str, 0)
        particle_render_mode = self.particle_render_mode_optionmenu.get().lower().replace(" ", "_")
        vsync_enabled = bool(self.enable_vsync_checkbox.get())
        sound_enabled = self.sound_enabled_checkbox.get()

        benchmark_functions = BENCHMARKS

        # Clear previous results and prepare BenchmarkManager
        self.benchmark_results = {}
        self.benchmark_manager = BenchmarkManager(self.stop_event)

        for benchmark_name in selected_benchmarks:
            if benchmark_name in benchmark_functions:
                self.benchmark_manager.add_benchmark(
                    name=benchmark_name,
                    run_function=benchmark_functions[benchmark_name],
                    resolution=(width, height),
                    msaa_level=msaa_level,
                    anisotropy=anisotropy,
                    shading_model=shading_model,
                    shadow_map_resolution=shadow_map_resolution,
                    particle_render_mode=particle_render_mode,
                    vsync_enabled=vsync_enabled,
                    sound_enabled=sound_enabled,
                    fullscreen=fullscreen,
                )
            else:
                tkinter.messagebox.showerror("Error", f"No benchmark found for {benchmark_name}")

        self.disable_widgets()
        self.show_loading_bar()
        threading.Thread(target=self.run_benchmarks_thread, daemon=True).start()

    def run_benchmarks_thread(self):
        self.benchmark_manager.run_benchmarks()
        # Hide the loading bar
        self.after(0, self.hide_loading_bar)
        if self.benchmark_manager.benchmark_stopped_by_user:
            # Benchmark was stopped by user
            self.after(0, lambda: tkinter.messagebox.showinfo("Benchmark Stopped", "Benchmark stopped by user."))
        else:
            if self.is_demo_mode:
                # Demo mode completed; show popup
                self.after(
                    0, lambda: tkinter.messagebox.showinfo("Demo Completed", "Thanks for running the Fragment demo!")
                )
            else:
                # Store results
                self.benchmark_results = self.benchmark_manager.get_results()
                # Display results
                self.after(0, self.generate_and_display_results)
                # Switch to the "Results" tab
                self.after(0, lambda: self.tabview.set("Results"))
        # Re-enable widgets
        self.after(0, self.enable_widgets)
        # Reset Demo Mode flag
        self.is_demo_mode = False

    def demo_mode(self):
        self.disable_widgets()
        resolution_str = self.resolution_optionmenu.get()
        if resolution_str == "Fullscreen":
            width, height = self.desktop_info.current_w, self.desktop_info.current_h
            fullscreen = True
        else:
            try:
                width, height = map(int, resolution_str.split("x"))
                fullscreen = False
            except ValueError:
                tkinter.messagebox.showerror("Invalid Resolution", "Please select a valid resolution.")
                self.enable_widgets()
                return

        try:
            msaa_level = int(self.msaa_level_optionmenu.get())
        except ValueError:
            msaa_level = 0

        try:
            anisotropy = int(self.anisotropy_optionmenu.get())
        except ValueError:
            anisotropy = 1

        # NEW: Retrieve the selected shading model for demo mode
        shading_model = self.shading_model_optionmenu.get().lower()

        shadow_quality_str = self.shadow_quality_optionmenu.get()
        shadow_map_resolution = self.shadow_quality_mapping.get(shadow_quality_str, 0)
        particle_render_mode = self.particle_render_mode_optionmenu.get().lower().replace(" ", "_")
        vsync_enabled = bool(self.enable_vsync_checkbox.get())
        sound_enabled = self.sound_enabled_checkbox.get()

        # Prepare parameters for the demo benchmark
        demo_parameters = {
            "resolution": (width, height),
            "msaa_level": msaa_level,
            "anisotropy": anisotropy,
            "shading_model": shading_model,
            "shadow_map_resolution": shadow_map_resolution,
            "particle_render_mode": particle_render_mode,
            "vsync_enabled": vsync_enabled,
            "sound_enabled": sound_enabled,
            "fullscreen": fullscreen,
        }

        self.benchmark_manager = BenchmarkManager(self.stop_event)
        self.benchmark_manager.add_benchmark(
            name="Demo Mode",
            run_function=run_water_pyramid_benchmark,
            resolution=demo_parameters["resolution"],
            msaa_level=demo_parameters["msaa_level"],
            anisotropy=demo_parameters["anisotropy"],
            shading_model=demo_parameters["shading_model"],
            shadow_map_resolution=demo_parameters["shadow_map_resolution"],
            particle_render_mode=demo_parameters["particle_render_mode"],
            vsync_enabled=demo_parameters["vsync_enabled"],
            sound_enabled=demo_parameters["sound_enabled"],
            fullscreen=demo_parameters["fullscreen"],
        )

        self.is_demo_mode = True
        self.show_loading_bar()
        threading.Thread(target=self.run_benchmarks_thread, daemon=True).start()

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
        window.geometry(f"{width}x{height}+{x}+{y}")

    def show_about_info(self):
        about_window = customtkinter.CTkToplevel(self)
        about_window.iconbitmap(os.path.join(self.image_folder, "small_icon.ico"))
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
        icon_image = Image.open(os.path.join(self.image_folder, "large_icon.ico"))
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

        version_label = customtkinter.CTkLabel(about_window, text=f"Version {__version__}", font=("Arial", 12))
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

        about_window.after(
            250, lambda: about_window.iconbitmap(os.path.join(self.image_folder, "small_icon.ico"))
        )  # Restore icon after a delay (prevents default icon)

    def generate_and_display_results(self):
        # Destroy the current results frame to reset the scroll position
        self.results_frame.destroy()

        # Recreate the results frame with the same configurations
        self.results_frame = customtkinter.CTkScrollableFrame(self.tabview.tab("Results"))
        self.results_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        self.results_frame.grid_rowconfigure(0, weight=1)

        # Clear previous images and data
        self.plot_labels = []
        self.plot_images = []
        self.original_images = []
        self.axes_list = []
        self.figures = []

        # Switch to the "Results" tab
        self.after(0, lambda: self.tabview.set("Results"))

        # Continue with displaying the results
        self.after(0, self.display_results)

        # Calculate and display the performance score
        performance_score = self.benchmark_manager.calculate_performance_score()
        self.after(0, lambda: self.display_performance_score(performance_score))

    def display_performance_score(self, score):
        self.performance_score_label.configure(text=f"Performance Score: {score}")

    def display_results(self):
        self.show_loading_bar()
        try:
            plot_style.use("mpl20")

            # Clear previous images and widgets
            for widget in self.results_frame.winfo_children():
                widget.destroy()
            self.plot_labels = []
            self.plot_images = []
            self.original_images = []
            self.axes_list = []
            self.figures = []

            # Determine colors based on current mode
            current_mode = customtkinter.get_appearance_mode()
            if current_mode == "Dark":
                bar_color = "skyblue"
                line_colors = ["yellow", "cyan", "magenta"]
                self.chart_bg_color = "#2c2c2c"
                self.chart_text_color = "#b0b0b0"
            else:
                bar_color = "blue"
                line_colors = ["red", "green", "purple"]
                self.chart_bg_color = "#f0f0f0"
                self.chart_text_color = "#202020"

            if not self.benchmark_results:
                return

            widget_scaling = self.current_scaling
            base_font_size = 10
            min_font_size = 8
            scaled_font_size = max(base_font_size * widget_scaling, min_font_size)
            scaled_title_size = max(12 * widget_scaling, min_font_size)
            scaled_label_size = max(11 * widget_scaling, min_font_size)

            plt.rcParams.update(
                {
                    "font.size": scaled_font_size,
                    "axes.titlesize": scaled_title_size,
                    "axes.labelsize": scaled_label_size,
                    "xtick.labelsize": scaled_font_size,
                    "ytick.labelsize": scaled_font_size,
                    "legend.fontsize": scaled_font_size,
                }
            )

            # Update results textbox
            self.results_textbox.delete("1.0", tkinter.END)
            self.results_textbox.insert(tkinter.END, "Benchmark Results:\n\n")

            for idx, (benchmark_name, data) in enumerate(self.benchmark_results.items()):
                fps_data = data["fps_data"]
                cpu_usage_data = data["cpu_usage_data"]
                gpu_usage_data = data["gpu_usage_data"]
                elapsed_time = data["elapsed_time"]

                # Convert usage data to numpy arrays
                fps_data = np.array(fps_data, dtype=float)
                cpu_usage_data = np.array(cpu_usage_data, dtype=float)
                gpu_usage_data = np.array(gpu_usage_data, dtype=float)

                # Ensure arrays are at least 1D
                fps_data = np.atleast_1d(fps_data)
                cpu_usage_data = np.atleast_1d(cpu_usage_data)
                gpu_usage_data = np.atleast_1d(gpu_usage_data)

                # Clamp FPS data to non-negative
                fps_data = np.clip(fps_data, 0, None)

                # Generate the time axis based on the actual elapsed time
                if elapsed_time > 0 and len(fps_data) > 0:
                    interval = elapsed_time / len(fps_data)
                    time_data = np.array([i * interval for i in range(len(fps_data))])
                else:
                    time_data = np.arange(len(fps_data))

                # Handle CPU and GPU usage data
                cpu_usage_data = np.clip(cpu_usage_data, 0.0, 100.0)
                gpu_usage_data = np.clip(gpu_usage_data, 0.0, 100.0)

                # Desired sampling interval in seconds (you can adjust as needed)
                desired_sampling_interval = 1  # For example, every 1 second

                # Calculate the total number of data points
                total_data_points = len(time_data)

                # Calculate the total elapsed time
                if len(time_data) > 0:
                    total_time = time_data[-1] - time_data[0]
                else:
                    total_time = 0

                # Calculate the approximate number of samples desired
                if desired_sampling_interval > 0:
                    approx_samples = int(total_time / desired_sampling_interval)
                else:
                    approx_samples = total_data_points

                # Calculate the sampling factor
                if approx_samples > 0 and total_data_points > 0:
                    sampling_factor = max(1, total_data_points // approx_samples)
                else:
                    sampling_factor = 1

                # Apply sampling
                indices = np.arange(0, total_data_points, sampling_factor)
                # Ensure at least 2 data points for interpolation
                if len(indices) < 2:
                    indices = np.arange(total_data_points)

                # Sample the data
                time_data_sampled = time_data[indices]
                fps_data_sampled = fps_data[indices]
                cpu_usage_sampled = cpu_usage_data[indices]
                gpu_usage_sampled = gpu_usage_data[indices]

                # Interpolate FPS data
                if len(fps_data_sampled) > 3:
                    try:
                        fps_spline = make_interp_spline(time_data_sampled, fps_data_sampled, k=3)
                        time_data_fine = np.linspace(
                            time_data_sampled.min(), time_data_sampled.max(), len(time_data_sampled) * 10
                        )
                        fps_smooth = fps_spline(time_data_fine)
                    except Exception as e:
                        print(f"Could not interpolate FPS data for {benchmark_name}: {e}")
                        time_data_fine = time_data_sampled
                        fps_smooth = fps_data_sampled
                else:
                    # Not enough data points to interpolate
                    time_data_fine = time_data_sampled
                    fps_smooth = fps_data_sampled

                # **Clamp the interpolated FPS data to non-negative**
                fps_smooth = np.clip(fps_smooth, 0, None)

                # Interpolate CPU usage data
                cpu_usage = cpu_usage_sampled
                cpu_time = time_data_sampled
                if len(cpu_usage) > 3:
                    try:
                        cpu_spline = make_interp_spline(cpu_time, cpu_usage, k=3)
                        cpu_time_fine = np.linspace(cpu_time.min(), cpu_time.max(), len(cpu_time) * 10)
                        cpu_smooth = cpu_spline(cpu_time_fine)
                    except Exception as e:
                        print(f"Could not interpolate CPU usage data for {benchmark_name}: {e}")
                        cpu_time_fine = cpu_time
                        cpu_smooth = cpu_usage
                else:
                    cpu_time_fine = cpu_time
                    cpu_smooth = cpu_usage

                # Interpolate GPU usage data
                gpu_usage = gpu_usage_sampled
                gpu_time = time_data_sampled
                if len(gpu_usage) > 3:
                    try:
                        gpu_spline = make_interp_spline(gpu_time, gpu_usage, k=3)
                        gpu_time_fine = np.linspace(gpu_time.min(), gpu_time.max(), len(gpu_time) * 10)
                        gpu_smooth = gpu_spline(gpu_time_fine)
                    except Exception as e:
                        print(f"Could not interpolate GPU usage data for {benchmark_name}: {e}")
                        gpu_time_fine = gpu_time
                        gpu_smooth = gpu_usage
                else:
                    gpu_time_fine = gpu_time
                    gpu_smooth = gpu_usage

                num_benchmarks = len(self.benchmark_results)

                # Set figure size based on the results frame size
                self.results_frame.update_idletasks()
                window_width = self.results_frame.winfo_width() - 40  # Adjust for padding
                fig_width = max(window_width / 100, 6)  # Ensure minimum width
                fig_height_per_benchmark = 4  # Height in inches per benchmark
                fig_height = fig_height_per_benchmark * num_benchmarks

                # Create figure
                fig = plt.figure(figsize=(fig_width, fig_height), facecolor="none", dpi=100)

                # Create gridspec
                gs = fig.add_gridspec(nrows=num_benchmarks * 2, ncols=2, height_ratios=[0.3, 1] * num_benchmarks)

                # Title axes
                ax_title = fig.add_subplot(gs[0, :])
                ax_title.axis("off")
                ax_title.text(
                    0.5,
                    0.5,
                    benchmark_name,
                    ha="center",
                    va="center",
                    fontsize=scaled_title_size,
                    fontweight="bold",
                    color=self.chart_text_color,
                )

                # FPS plot
                ax_fps = fig.add_subplot(gs[1, 0])

                # CPU/GPU Usage plot
                ax_usage = fig.add_subplot(gs[1, 1])

                # Log data points
                avg_fps = np.nanmean(fps_data) if fps_data.size > 0 else 0

                # Store the axes for later adjustments
                self.axes_list.append((ax_title, ax_fps, ax_usage))

                # FPS Line Graph
                ax_fps.plot(time_data_fine, fps_smooth, color=bar_color)
                ax_fps.set_title("FPS Over Time")
                ax_fps.set_xlabel("Time (s)")
                ax_fps.set_ylabel("FPS")

                # CPU/GPU Usage Line Graph using interpolated data
                # Plot CPU usage
                if len(cpu_time_fine) > 0:
                    ax_usage.plot(cpu_time_fine, cpu_smooth, label="CPU Usage", linestyle="--", color=line_colors[0])
                else:
                    print(f"No CPU usage data to plot for {benchmark_name}")

                # Plot GPU usage
                if len(gpu_time_fine) > 0:
                    ax_usage.plot(gpu_time_fine, gpu_smooth, label="GPU Usage", color=line_colors[1])
                else:
                    print(f"No GPU usage data to plot for {benchmark_name}")

                ax_usage.set_title("CPU and GPU Usage Over Time")
                ax_usage.set_xlabel("Time (s)")
                ax_usage.set_ylabel("Usage (%)")
                ax_usage.legend()

                # Set Y-axis limits between 0% and 100%
                ax_usage.set_ylim(0, 100)

                # Adjust chart mode
                self.adjust_chart_mode(axes=[ax_title, ax_fps, ax_usage])

                # Adjust layout
                fig.tight_layout(rect=[0, 0, 1, 1])  # Adjust as needed

                # Render the figure to an image
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                buf.seek(0)
                img = Image.open(buf)

                # Store the original image
                self.original_images.append(img)

                # Close the figure to free up memory
                plt.close(fig)

                # Ensure the frame's geometry is updated
                self.results_frame.update_idletasks()

                # Get the width of the frame
                window_width = self.results_frame.winfo_width() - 40  # Adjust for padding

                # Ensure new dimensions are positive
                new_width = max(window_width, 1)
                new_height = max(int(img.height * (new_width / img.width)), 1)

                # Resize the image to fit the frame
                img_resized = img.resize((new_width, new_height), Image.LANCZOS)

                # Convert to PhotoImage
                plot_photo_image = ImageTk.PhotoImage(img_resized)
                self.plot_images.append(plot_photo_image)  # Keep a reference to prevent garbage collection

                # Create a Label to display the image and store it
                plot_label = tkinter.Label(self.results_frame, image=plot_photo_image, bg=self.chart_bg_color)
                plot_label.pack(padx=20, pady=(5, 10), fill="both", expand=True)
                self.plot_labels.append(plot_label)

                # Insert text results
                self.results_textbox.insert(tkinter.END, f"- {benchmark_name}: {avg_fps:.2f} Avg. FPS\n")

            # Update the results_frame background color
            self.results_frame.configure(fg_color=self.chart_bg_color)

            # Schedule adjust_image_sizes to be called after the GUI has updated
            self.after(0, self.adjust_image_sizes)
        finally:
            self.hide_loading_bar()  # Ensure the loading bar is hidden after rendering

    def adjust_image_sizes(self):
        # Ensure the results_frame's geometry is updated
        self.results_frame.update_idletasks()
        window_width = self.results_frame.winfo_width() - 40  # Adjust for padding

        for idx, plot_label in enumerate(self.plot_labels):
            # Get the original image
            original_image = self.original_images[idx]

            # Calculate scale factor to fit the image within the results frame
            scale_factor = window_width / original_image.width
            new_width = int(original_image.width * scale_factor)
            new_height = int(original_image.height * scale_factor)
            img_resized = original_image.resize((new_width, new_height), Image.LANCZOS)

            # Update the image
            plot_photo_image = ImageTk.PhotoImage(img_resized)
            self.plot_images[idx] = plot_photo_image  # Update the reference
            plot_label.configure(image=plot_photo_image)

    def on_window_resize(self, event=None):
        # Cancel any previous scheduled resizing for the image
        if hasattr(self, "_image_resize_after_id"):
            self.after_cancel(self._image_resize_after_id)

        # Schedule a new image resize to happen after 200 ms (or any delay you prefer)
        self._image_resize_after_id = self.after(200, self.resize_image_after_window_resize)

        # Get the root window
        root = self.winfo_toplevel()

        # Only proceed if the event was triggered by the root window
        if event is not None and event.widget != root:
            return

        new_size = (self.winfo_width(), self.winfo_height())
        if hasattr(self, "last_window_size") and self.last_window_size == new_size:
            return  # Size hasn't changed, no need to proceed

        self.last_window_size = new_size

        if self.is_resizing:
            return  # Ignore resize events during resizing

        # Start the resizing flag
        self.is_resizing = True

        # Cancel any previous scheduled resizing
        if hasattr(self, "resize_after_id") and self.resize_after_id:
            self.after_cancel(self.resize_after_id)

        # Schedule resizing after 500 milliseconds
        self.resize_after_id = self.after(500, lambda: self.on_resize_complete())
        self.is_resizing = False  # Reset the resizing flag

    def resize_image_after_window_resize(self):
        # Logic for resizing the image after the window resize
        if self.currently_selected_benchmark_name:
            self.display_image(self.currently_selected_benchmark_name)

    def adjust_chart_mode(self, axes=None):
        # Get the effective appearance mode
        mode = customtkinter.get_appearance_mode()

        # Set chart colors regardless of whether axes are initialized
        if mode == "Dark":
            self.chart_bg_color = "#2c2c2c"
            self.chart_text_color = "#b0b0b0"
        else:
            self.chart_bg_color = "#f0f0f0"
            self.chart_text_color = "#202020"

        if axes is None:
            # If no axes provided, use the stored axes
            if not hasattr(self, "axes_list") or not self.axes_list:
                print("Charts not initialized yet.")
                return
            axes_list = [ax for axes_tuple in self.axes_list for ax in axes_tuple]
        else:
            axes_list = axes

        # Update axes and text colors
        for ax in axes_list:
            ax.set_facecolor(self.chart_bg_color)
            ax.tick_params(axis="x", colors=self.chart_text_color)
            ax.tick_params(axis="y", colors=self.chart_text_color)
            ax.xaxis.label.set_color(self.chart_text_color)
            ax.yaxis.label.set_color(self.chart_text_color)
            ax.title.set_color(self.chart_text_color)

            # Set spines' edge color
            for spine in ax.spines.values():
                spine.set_edgecolor(self.chart_text_color)

            # Remove grid lines if desired
            ax.grid(False)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)
        self.adjust_chart_mode()
        self.update_results_background()  # Update the background colors

        # Re-render the chart to apply theme changes
        if self.benchmark_results:
            self.display_results()

    def change_scaling_event(self, new_scaling: str):
        # Parse new scaling factor
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

        # Store the new scaling factor
        self.current_scaling = new_scaling_float

        # Update the chart size based on the new scaling factor
        self.update_chart_scaling()

    def update_chart_scaling(self):
        # Re-render the chart with updated scaling
        if self.benchmark_results:
            self.display_results()

    def exit_app(self):
        try:
            # Cancel any pending resize operation
            if hasattr(self, "resize_after_id") and self.resize_after_id:
                self.after_cancel(self.resize_after_id)
            # Signal benchmarks to stop
            self.stop_event.set()

            # Stop the loading progress bar if it's running
            if self.loading_progress_bar:
                self.loading_progress_bar.stop()

            # Cancel all pending 'after' callbacks
            after_ids = self.tk.call("after", "info")
            for after_id in self.tk.splitlist(after_ids):
                try:
                    self.after_cancel(after_id)
                except:
                    pass

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

    def on_demo_hover(self, event):
        if self.tabview.get() == "Scenarios":
            self.display_demo_image()

    def on_demo_leave(self, event):
        # Clear the image area only if the demo was the last hovered element
        if self.currently_selected_benchmark_name == "Shimmer (Demo)":
            self.image_area.configure(image=None)

    def display_demo_image(self):
        benchmark_name = "Shimmer (Demo)"
        self.currently_selected_benchmark_name = benchmark_name

        # Construct the path to the demo image file
        sanitized_name = (
            benchmark_name.replace(":", "")
            .replace("/", "")
            .replace("\\", "")
            .replace(")", "")
            .replace("(", "")
            .replace(" ", " - ")
        )
        image_path = os.path.join(self.image_folder, f"{sanitized_name}.png")

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
            self.displayed_image = CTkImage(
                light_image=img_resized, dark_image=img_resized, size=(image_area_width, image_area_height)
            )

            # Apply the resized image with shadow and set the area size
            self.image_area.configure(image=self.displayed_image, width=image_area_width, height=image_area_height)

            # Keep a reference to prevent garbage collection
            self.image_area.image = self.displayed_image
        else:
            self.image_area.configure(image=None)  # Clear if no image found
