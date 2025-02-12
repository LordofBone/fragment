import threading
import time

import psutil
import pygame
from GPUtil import getGPUs
from OpenGL.GL import *


class RendererWindow:
    """
    RendererWindow manages a Pygame-based OpenGL rendering window:
    - Window creation (with optional fullscreen, vsync, MSAA)
    - Event handling (closing, ESC key, etc.)
    - FPS title bar updates
    - Background thread to monitor CPU/GPU usage
    """

    def __init__(
            self,
            window_size=(800, 600),
            title="Renderer",
            msaa_level=4,
            vsync_enabled=True,
            fullscreen=False
    ):
        """
        Initialize the window parameters, prepare Pygame, and start the system usage monitoring thread.

        Args:
            window_size (tuple): (width, height) of the window.
            title (str): The title to display in the window bar.
            msaa_level (int): Level of MSAA anti-aliasing.
            vsync_enabled (bool): Whether to enable VSync (if supported).
            fullscreen (bool): If True, creates a fullscreen window.
        """
        # ----------------------------------------------------------------------
        # Window and Rendering Config
        # ----------------------------------------------------------------------
        self.window_size = window_size
        self.title = title
        self.msaa_level = msaa_level
        self.vsync_enabled = vsync_enabled
        self.fullscreen = fullscreen

        # ----------------------------------------------------------------------
        # Internal State
        # ----------------------------------------------------------------------
        self.clock = None
        self.running = True
        self.should_close = False

        # ----------------------------------------------------------------------
        # CPU & GPU Usage Monitoring
        # ----------------------------------------------------------------------
        self.cpu_usage = 0.0
        self.gpu_usage = 0.0
        self.usage_lock = threading.Lock()
        self.monitoring_event = threading.Event()  # Signal to stop monitoring

        # ----------------------------------------------------------------------
        # Pygame Setup and OpenGL Initialization
        # ----------------------------------------------------------------------
        self.setup_pygame()
        self.clock = pygame.time.Clock()

        # ----------------------------------------------------------------------
        # Start Background Monitoring Thread
        # ----------------------------------------------------------------------
        self.monitoring_thread = threading.Thread(
            target=self.monitor_system_usage,
            daemon=True
        )
        self.monitoring_thread.start()

    # --------------------------------------------------------------------------
    # Pygame and OpenGL Setup
    # --------------------------------------------------------------------------
    def setup_pygame(self):
        """
        Initialize Pygame, configure OpenGL attributes, and open the display.
        """
        pygame.init()
        self.configure_opengl_attributes()

        if self.fullscreen:
            # Match the desktop resolution for fullscreen
            desktop_info = pygame.display.Info()
            self.window_size = (desktop_info.current_w, desktop_info.current_h)

        display_flags = pygame.DOUBLEBUF | pygame.OPENGL
        if self.fullscreen:
            display_flags |= pygame.FULLSCREEN

        # Attempt to set vsync if supported
        try:
            pygame.display.set_mode(
                self.window_size,
                display_flags,
                vsync=1 if self.vsync_enabled else 0
            )
        except TypeError:
            # For older Pygame versions that do not support vsync argument
            pygame.display.set_mode(self.window_size, display_flags)
            print("Warning: VSync not supported by your Pygame version.")

        # Set initial window title and font
        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)

        # Enable multisample anti-aliasing
        glEnable(GL_MULTISAMPLE)

    def configure_opengl_attributes(self):
        """
        Configure OpenGL attributes for multisampling.
        """
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.msaa_level)

    # --------------------------------------------------------------------------
    # System Usage Monitoring (Background Thread)
    # --------------------------------------------------------------------------
    def monitor_system_usage(self):
        """
        Continuously monitor CPU and GPU usage in a background thread
        and update shared usage variables.
        """
        while not self.monitoring_event.is_set():
            # Fetch CPU usage
            cpu = psutil.cpu_percent(interval=None)

            # Fetch GPU usage (sum load across all GPUs if multiple)
            try:
                gpus = getGPUs()
                if gpus:
                    gpu = sum(gpu.load * 100 for gpu in gpus)
                else:
                    gpu = 0.0
            except Exception as e:
                print(f"Error retrieving GPU usage: {e}")
                gpu = 0.0

            # Update shared usage variables with a lock
            with self.usage_lock:
                self.cpu_usage = cpu
                self.gpu_usage = gpu

            # Sleep for 1 second before next update
            time.sleep(1)

    # --------------------------------------------------------------------------
    # Window Title and FPS
    # --------------------------------------------------------------------------
    def draw_fps_in_title(self, fps):
        """
        Update the window title with FPS, CPU usage, and GPU usage.

        Args:
            fps (float): Current frames per second.
        """
        with self.usage_lock:
            cpu = self.cpu_usage
            gpu = self.gpu_usage

        new_title = f"{self.title} - FPS: {fps:.2f} | CPU: {cpu:.1f}% | GPU: {gpu:.1f}%"
        pygame.display.set_caption(new_title)

    # --------------------------------------------------------------------------
    # Event Handling
    # --------------------------------------------------------------------------
    def handle_events(self):
        """
        Process incoming Pygame events.

        Returns:
            bool: True if the window should close, False otherwise.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_close = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.should_close = True

        return self.should_close

    # --------------------------------------------------------------------------
    # Display Handling
    # --------------------------------------------------------------------------
    def display_flip(self):
        """
        Swap the front and back buffers to display the newly rendered frame.
        """
        pygame.display.flip()

    # --------------------------------------------------------------------------
    # Shutdown and Cleanup
    # --------------------------------------------------------------------------
    def shutdown(self):
        """
        Stop monitoring, wait for the thread to finish, and quit Pygame.
        """
        self.running = False
        self.monitoring_event.set()  # Signal the monitoring thread to stop
        self.monitoring_thread.join()
        pygame.quit()
