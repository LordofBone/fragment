import pygame
from OpenGL.GL import *
from OpenGL.GLUT import *


class RenderWindow:
    def __init__(self, window_size=(800, 600), title="Render Window"):
        self.window_size = window_size
        self.title = title
        self.clock = None

        self.setup_pygame()
        self.clock = pygame.time.Clock()

    def setup_pygame(self):
        pygame.init()
        pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL)
        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)

    def draw_fps(self):
        fps = str(int(self.clock.get_fps()))
        fps_surface = self.font.render(fps, True, pygame.Color('white'))
        fps_data = pygame.image.tostring(fps_surface, "RGBA", True)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glWindowPos2i(self.window_size[0] - fps_surface.get_width() - 10, 20)
        glDrawPixels(fps_surface.get_width(), fps_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, fps_data)

        glDisable(GL_BLEND)

    def mainloop(self, render_callback):
        glEnable(GL_DEPTH_TEST)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            render_callback()

            self.draw_fps()
            pygame.display.flip()
            self.clock.tick(60)
