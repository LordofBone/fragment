import pygame
from OpenGL.GL import *
from OpenGL.GLUT import *


class RendererWindow:
    def __init__(self, window_size=(800, 600), title="Renderer", msaa_level=4, vsync_enabled=True):
        self.window_size = window_size
        self.title = title
        self.msaa_level = msaa_level
        self.vsync_enabled = vsync_enabled
        self.clock = None
        self.running = True  # Control the main loop
        self.should_close = False  # Flag to indicate window should close

        self.setup_pygame()
        self.clock = pygame.time.Clock()

    def setup_pygame(self):
        """Setup Pygame for OpenGL rendering."""
        pygame.init()
        self.configure_opengl_attributes()
        pygame.display.set_mode(self.window_size, pygame.DOUBLEBUF | pygame.OPENGL,
                                vsync=1 if self.vsync_enabled else 0)
        pygame.display.set_caption(self.title)
        pygame.font.init()
        self.font = pygame.font.Font(None, 36)
        glEnable(GL_MULTISAMPLE)

    def configure_opengl_attributes(self):
        """Configure OpenGL attributes for Pygame."""
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, self.msaa_level)

    def draw_fps(self, fps):
        """Draw the FPS on the screen."""
        fps = str(int(fps))
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
        # Render the FPS text as a Pygame surface
        fps_surface = self.font.render(fps, True, pygame.Color("white"))

        # Set the position to the top-right corner with some padding (10 pixels from the right edge and 20 pixels from the top edge)
        glWindowPos2i(self.window_size[0] - fps_surface.get_width() - 10,
                      self.window_size[1] - fps_surface.get_height() - 10)

        # Draw the FPS text as OpenGL pixels
        glDrawPixels(fps_surface.get_width(), fps_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, fps_data)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.should_close = True  # Set the flag instead of shutting down
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.should_close = True  # Set the flag if Escape is pressed

        return self.should_close

    def display_flip(self):
        """Update the display."""
        pygame.display.flip()

    def shutdown(self):
        """Shutdown the renderer window."""
        self.running = False
        pygame.quit()
