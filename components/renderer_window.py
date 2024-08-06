import time

import pygame
from OpenGL.GL import *
from OpenGL.GLUT import *


class RendererWindow:
    def __init__(self, window_size=(800, 600), title="Render Window", msaa_level=4):
        self.window_size = window_size
        self.title = title
        self.msaa_level = msaa_level
        self.clock = None

        self.setup_pygame()
        self.clock = pygame.time.Clock()

    def setup_pygame(self):
        """Setup Pygame for OpenGL rendering."""
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.msaa_level)

        pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        glEnable(GL_MULTISAMPLE)

    def draw_fps(self):
        """Draw the FPS on the screen."""
        fps = str(int(self.clock.get_fps()))
        fps_surface = self.font.render(fps, True, pygame.Color('white'))
        fps_data = pygame.image.tostring(fps_surface, "RGBA", True)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glWindowPos2i(self.window_size[0] - fps_surface.get_width() - 10, 20)
        glDrawPixels(fps_surface.get_width(), fps_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, fps_data)

        glDisable(GL_BLEND)

    def mainloop(self, render_callback):
        """Main rendering loop."""
        glEnable(GL_DEPTH_TEST)
        last_time = time.time()
        while True:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            render_callback(delta_time)

            self.draw_fps()
            pygame.display.flip()
            self.clock.tick(60)
