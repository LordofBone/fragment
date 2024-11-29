import glm
from OpenGL.GL import *

from utils.decorators import singleton


@singleton
class ShadowMapManager:
    def __init__(self, shadow_width=1024, shadow_height=1024):
        self.shadow_width = shadow_width
        self.shadow_height = shadow_height
        self.depth_map_fbo = glGenFramebuffers(1)
        self.depth_map = glGenTextures(1)
        self.light_space_matrix = glm.mat4(1)

        # Initialize depth map texture and framebuffer
        self._initialize_depth_map()

    def _initialize_depth_map(self):
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
        borderColor = [1.0, 1.0, 1.0, 1.0]
        glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, borderColor)

        glBindFramebuffer(GL_FRAMEBUFFER, self.depth_map_fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.depth_map, 0)
        glDrawBuffer(GL_NONE)
        glReadBuffer(GL_NONE)

        # Check for completeness
        status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if status != GL_FRAMEBUFFER_COMPLETE:
            print("Shadow Map Framebuffer is not complete:", status)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def setup(self, light, near_plane=1.0, far_plane=50.0):
        light_projection = glm.ortho(
            light["orth_left"], light["orth_right"], light["orth_bottom"], light["orth_top"], near_plane, far_plane
        )
        light_view = glm.lookAt(light["position"], glm.vec3(0.0, 0.0, 0.0), glm.vec3(0.0, 1.0, 0.0))
        self.light_space_matrix = light_projection * light_view
