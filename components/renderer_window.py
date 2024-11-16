import psutil
import pygame
from GPUtil import getGPUs
from OpenGL.GL import *


class RendererWindow:
    def __init__(self, window_size=(800, 600), title="Renderer", msaa_level=4, vsync_enabled=True, fullscreen=False):
        self.window_size = window_size
        self.title = title
        self.msaa_level = msaa_level
        self.vsync_enabled = vsync_enabled
        self.fullscreen = fullscreen
        self.clock = None
        self.running = True
        self.should_close = False

        self.setup_pygame()
        self.clock = pygame.time.Clock()

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

        pygame.display.set_mode(self.window_size, display_flags, vsync=1 if self.vsync_enabled else 0)
        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        glEnable(GL_MULTISAMPLE)

    def configure_opengl_attributes(self):
        """Configure OpenGL attributes for Pygame."""
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.msaa_level)

    def draw_fps_in_title(self, fps):
        """
        Update the window title with the current FPS, CPU, and GPU usage.

        :param fps: Current frames per second.
        """
        cpu_usage = psutil.cpu_percent(interval=None)
        gpu_usage = self.get_gpu_usage()
        new_title = f"{self.title} - FPS: {fps:.2f} | CPU: {cpu_usage:.1f}% | GPU: {gpu_usage:.1f}%"
        pygame.display.set_caption(new_title)

    def get_gpu_usage(self):
        """
        Calculate the overall GPU usage across all available GPUs.

        :return: Total GPU usage as a percentage.
        """
        try:
            gpus = getGPUs()
            if not gpus:
                return 0.0
            total_gpu_usage = sum(gpu.load * 100 for gpu in gpus)
            # Clamp the value between 0 and 100
            total_gpu_usage = max(min(total_gpu_usage, 100.0), 0.0)
            return total_gpu_usage
        except Exception as e:
            print(f"Error retrieving GPU usage: {e}")
            return 0.0

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
        """Shutdown the renderer window."""
        self.running = False
        pygame.quit()
