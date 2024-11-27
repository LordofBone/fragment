import threading
import time

import psutil
import pygame
from GPUtil import getGPUs
from OpenGL.GL import *


class RendererWindow:
    def __init__(self, window_size=(800, 600), title="Renderer", msaa_level=4, shadow_map_resolution=1024,
                 vsync_enabled=True, fullscreen=False):
        self.window_size = window_size
        self.title = title
        self.msaa_level = msaa_level
        self.shadow_map_resolution = shadow_map_resolution
        self.vsync_enabled = vsync_enabled
        self.fullscreen = fullscreen
        self.clock = None
        self.running = True
        self.should_close = False

        # Shared variables for CPU and GPU usage
        self.cpu_usage = 0.0
        self.gpu_usage = 0.0
        self.usage_lock = threading.Lock()

        # Event to signal the monitoring thread to stop
        self.monitoring_event = threading.Event()

        self.setup_pygame()
        self.clock = pygame.time.Clock()

        # Start the monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitor_system_usage, daemon=True)
        self.monitoring_thread.start()

    def setup_pygame(self):
        """Setup Pygame for OpenGL rendering."""
        pygame.init()
        self.configure_opengl_attributes()

        if self.fullscreen:
            # Get the desktop resolution
            desktop_info = pygame.display.Info()
            self.window_size = (desktop_info.current_w, desktop_info.current_h)

        display_flags = pygame.DOUBLEBUF | pygame.OPENGL
        if self.fullscreen:
            display_flags |= pygame.FULLSCREEN

        # Attempt to set vsync; if pygame doesn't support it, handle gracefully
        try:
            pygame.display.set_mode(self.window_size, display_flags, vsync=1 if self.vsync_enabled else 0)
        except TypeError:
            # Pygame version might not support vsync parameter
            pygame.display.set_mode(self.window_size, display_flags)
            print("Warning: VSync not supported by your Pygame version.")

        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        glEnable(GL_MULTISAMPLE)

    def configure_opengl_attributes(self):
        """Configure OpenGL attributes for Pygame."""
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.msaa_level)

    def monitor_system_usage(self):
        """
        Background thread to monitor CPU and GPU usage.
        Updates shared variables without blocking the main thread.
        """
        while not self.monitoring_event.is_set():
            # Fetch CPU usage
            cpu = psutil.cpu_percent(interval=None)

            # Fetch GPU usage
            try:
                gpus = getGPUs()
                if gpus:
                    gpu = sum(gpu.load * 100 for gpu in gpus)
                else:
                    gpu = 0.0
            except Exception as e:
                print(f"Error retrieving GPU usage: {e}")
                gpu = 0.0

            # Update shared variables
            with self.usage_lock:
                self.cpu_usage = cpu
                self.gpu_usage = gpu

            # Sleep for 1 second before next update
            time.sleep(1)

    def draw_fps_in_title(self, fps):
        """
        Update the window title with the current FPS, CPU, and GPU usage.

        :param fps: Current frames per second.
        """
        with self.usage_lock:
            cpu = self.cpu_usage
            gpu = self.gpu_usage

        new_title = f"{self.title} - FPS: {fps:.2f} | CPU: {cpu:.1f}% | GPU: {gpu:.1f}%"
        pygame.display.set_caption(new_title)

    def handle_events(self):
        """
        Handle incoming Pygame events.

        :return: Boolean indicating whether the window should close.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_close = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.should_close = True

        return self.should_close

    def display_flip(self):
        """Update the display."""
        pygame.display.flip()

    def shutdown(self):
        """Shutdown the renderer window and stop the monitoring thread."""
        self.running = False
        self.monitoring_event.set()
        self.monitoring_thread.join()
        pygame.quit()
