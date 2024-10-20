import tkinter
import tkinter.messagebox

import customtkinter

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


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

        # Main content area
        self.tabview = customtkinter.CTkTabview(self, width=600)
        self.tabview.grid(row=0, column=1, columnspan=4, rowspan=5, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.tabview.add("Graphics Settings")
        self.tabview.add("Benchmark Selection")
        self.tabview.add("Results")

        # Graphics settings tab
        self.tabview.tab("Graphics Settings").grid_columnconfigure(0, weight=1)
        self.resolution_label = customtkinter.CTkLabel(self.tabview.tab("Graphics Settings"), text="Resolution:")
        self.resolution_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.resolution_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Graphics Settings"),
                                                                 values=["640x480", "800x600", "1024x768", "1280x720",
                                                                         "1920x1080"])
        self.resolution_optionmenu.grid(row=0, column=1, padx=20, pady=(20, 10))

        self.texture_quality_label = customtkinter.CTkLabel(self.tabview.tab("Graphics Settings"),
                                                            text="Texture Quality:")
        self.texture_quality_label.grid(row=1, column=0, padx=20, pady=(20, 10))
        self.texture_quality_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Graphics Settings"),
                                                                      values=["Low", "Medium", "High", "Ultra"])
        self.texture_quality_optionmenu.grid(row=1, column=1, padx=20, pady=(20, 10))

        self.shadow_quality_label = customtkinter.CTkLabel(self.tabview.tab("Graphics Settings"),
                                                           text="Shadow Quality:")
        self.shadow_quality_label.grid(row=2, column=0, padx=20, pady=(20, 10))
        self.shadow_quality_optionmenu = customtkinter.CTkOptionMenu(self.tabview.tab("Graphics Settings"),
                                                                     values=["Low", "Medium", "High", "Ultra"])
        self.shadow_quality_optionmenu.grid(row=2, column=1, padx=20, pady=(20, 10))

        self.enable_vsync_checkbox = customtkinter.CTkCheckBox(self.tabview.tab("Graphics Settings"),
                                                               text="Enable V-Sync")
        self.enable_vsync_checkbox.grid(row=3, column=0, columnspan=2, padx=20, pady=(20, 10))

        # Benchmark selection tab
        self.tabview.tab("Benchmark Selection").grid_columnconfigure(0, weight=1)
        self.benchmark_list_label = customtkinter.CTkLabel(self.tabview.tab("Benchmark Selection"),
                                                           text="Select Benchmark Tests:")
        self.benchmark_list_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Using tkinter Listbox
        self.benchmark_listbox = tkinter.Listbox(self.tabview.tab("Benchmark Selection"), selectmode="multiple",
                                                 height=10)
        self.benchmark_listbox.grid(row=1, column=0, padx=20, pady=(20, 10), sticky="nsew")
        for benchmark in ["Game 1 - Helicopter", "Game 2 - Adventure", "Fill Rate Test", "High Polygon Count Test"]:
            self.benchmark_listbox.insert(tkinter.END, benchmark)

        # Results tab
        self.results_textbox = customtkinter.CTkTextbox(self.tabview.tab("Results"), width=400, height=300)
        self.results_textbox.grid(row=0, column=0, padx=20, pady=(20, 20), sticky="nsew")

        # Set default values
        self.appearance_mode_optionemenu.set("System")
        self.scaling_optionemenu.set("100%")
        self.resolution_optionmenu.set("1024x768")
        self.texture_quality_optionmenu.set("High")
        self.shadow_quality_optionmenu.set("Medium")
        self.enable_vsync_checkbox.select()

    def run_benchmark(self):
        tkinter.messagebox.showinfo("Benchmark", "Running the selected benchmark...")

    def demo_mode(self):
        tkinter.messagebox.showinfo("Demo Mode", "Demo mode started...")

    def view_results(self):
        self.results_textbox.insert(tkinter.END, "Benchmark Results:\n\n- Game 1: 85.3 FPS\n- Game 2: 60.5 FPS\n...")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)


if __name__ == "__main__":
    app = App()
    app.mainloop()
