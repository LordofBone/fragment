import time

import pygame
from OpenGL.GL import *
from OpenGL.GLUT import *


class RendererWindow:
    def __init__(self, window_size=(800, 600), title="Renderer", msaa_level=4):
        self.window_size = window_size
        self.title = title
        self.msaa_level = msaa_level
        self.clock = None
        self.running = True  # Control the main loop

        self.setup_pygame()
        self.clock = pygame.time.Clock()

    def setup_pygame(self):
        """Setup Pygame for OpenGL rendering."""
        pygame.init()
        self.configure_opengl_attributes()
        pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        glEnable(GL_MULTISAMPLE)

    def configure_opengl_attributes(self):
        """Configure OpenGL attributes for Pygame."""
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.msaa_level)

    def draw_fps(self):
        """Draw the FPS on the screen."""
        fps = self.get_fps_text()
        fps_data = self.create_fps_texture(fps)

        self.enable_blending()
        self.draw_fps_texture(fps, fps_data)
        glDisable(GL_BLEND)

    def get_fps_text(self):
        return str(int(self.clock.get_fps()))

    def create_fps_texture(self, fps):
        fps_surface = self.font.render(fps, True, pygame.Color("white"))
        return pygame.image.tostring(fps_surface, "RGBA", True)

    def enable_blending(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def draw_fps_texture(self, fps, fps_data):
        fps_surface = self.font.render(fps, True, pygame.Color("white"))
        glWindowPos2i(self.window_size[0] - fps_surface.get_width() - 10, 20)
        glDrawPixels(fps_surface.get_width(), fps_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, fps_data)

    def mainloop(self, render_callback):
        """Main rendering loop."""
        glEnable(GL_DEPTH_TEST)
        last_time = time.time()
        while self.running:
            delta_time = self.calculate_delta_time(last_time)
            last_time = time.time()

            if self.handle_events():
                self.running = False
                break

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            render_callback(delta_time)

            self.draw_fps()
            pygame.display.flip()
            self.clock.tick(60)

    def calculate_delta_time(self, last_time):
        return time.time() - last_time

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return True
        return False

    def shutdown(self):
        """Shutdown the renderer window."""
        self.running = False
        pygame.quit()
