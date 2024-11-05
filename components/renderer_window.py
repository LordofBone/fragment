import pygame
from OpenGL.GL import *
from OpenGL.GLUT import *


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

        pygame.display.set_mode(self.window_size, display_flags,
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
        fps_text = str(int(fps))
        # Create the surface and texture data once
        fps_surface = self.font.render(fps_text, True, pygame.Color("white")).convert_alpha()
        fps_data = pygame.image.tostring(fps_surface, "RGBA", True)

        self.enable_blending()
        self.draw_fps_texture(fps_surface, fps_data)
        glDisable(GL_BLEND)

    def create_fps_texture(self, fps_surface):
        return pygame.image.tostring(fps_surface, "RGBA", True)

    def enable_blending(self):
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def draw_fps_texture(self, fps_surface, fps_data):
        # Set the pixel unpack alignment
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        # Position the text
        glWindowPos2i(self.window_size[0] - fps_surface.get_width() - 10,
                      self.window_size[1] - fps_surface.get_height() - 10)

        # Draw the FPS text as OpenGL pixels
        glDrawPixels(fps_surface.get_width(), fps_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, fps_data)

    def handle_events(self):
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
