import glm
from OpenGL.GL import *

from utils.decorators import singleton


@singleton
class ShadowMapManager:
    """
    Manages a depth framebuffer and texture used for shadow mapping.

    - Creates a depth map texture (2D) and a framebuffer for rendering shadows.
    - Calculates a light-space matrix from the given light parameters.
    """

    def __init__(self, shadow_width=1024, shadow_height=1024):
        """
        Initialize the shadow map with a specified width and height.
        """
        self.shadow_width = shadow_width
        self.shadow_height = shadow_height

        # FBO & Depth Texture
        self.depth_map_fbo = glGenFramebuffers(1)
        self.depth_map = glGenTextures(1)

        # Light-space transform
        self.light_space_matrix = glm.mat4(1)

        # Setup the depth map and associated framebuffer
        self._initialize_depth_map()

    def _initialize_depth_map(self):
        """
        Create the depth texture and attach it to the FBO.
        """
        glBindTexture(GL_TEXTURE_2D, self.depth_map)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_DEPTH_COMPONENT,
            self.shadow_width,
            self.shadow_height,
            0,
            GL_DEPTH_COMPONENT,
            GL_FLOAT,
            None,
        )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER)

        # For shadows, set the border color to white (1.0)
        borderColor = [1.0, 1.0, 1.0, 1.0]
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, borderColor)

        # Attach texture to the depth attachment of the FBO
        glBindFramebuffer(GL_FRAMEBUFFER, self.depth_map_fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.depth_map, 0)

        # No color buffer needed
        glDrawBuffer(GL_NONE)
        glReadBuffer(GL_NONE)

        # Check completeness
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            print("Shadow Map Framebuffer is not complete:", status)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def setup(self, light, near_plane=1.0, far_plane=50.0):
        """
        Compute the light-space matrix using orthographic projection
        and the light's position.

        Args:
            light (dict): Contains 'position', 'orth_left', 'orth_right',
                          'orth_bottom', 'orth_top', 'color', etc.
            near_plane (float): Near clipping distance for ortho frustum.
            far_plane (float): Far clipping distance for ortho frustum.
        """
        light_projection = glm.ortho(
            light["orth_left"],
            light["orth_right"],
            light["orth_bottom"],
            light["orth_top"],
            near_plane,
            far_plane
        )
        light_view = glm.lookAt(
            light["position"],
            glm.vec3(0.0, 0.0, 0.0),  # Look at origin or relevant scene center
            glm.vec3(0.0, 1.0, 0.0)  # Up vector
        )
        self.light_space_matrix = light_projection * light_view
