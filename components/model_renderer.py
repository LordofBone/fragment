import numpy as np
import pywavefront
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, common_funcs
from components.texture_manager import TextureManager

texture_manager = TextureManager()


class ModelRenderer(AbstractRenderer):
    def __init__(self, renderer_name, obj_path, **kwargs):
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.obj_path = obj_path
        # create_materials=True and collect_faces=True ensure we have materials and faces data
        self.object = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

        # 1) Create a default dict of fallback PBR params
        default_pbr = {
            "roughness": 0.5,
            "metallic": 0.0,
            "clearcoat": 0.0,
            "clearcoat_roughness": 0.03,
            "sheen": 0.0,
            "aniso": 0.0,
            "anisor": 0.0,
        }

        # 2) If user passed `pbr_extensions` in the constructor kwargs,
        #    override our defaults:
        user_pbr = kwargs.get("pbr_extensions", {})
        default_pbr.update(user_pbr)

        # 3) Store them in an instance attribute (a dict) so we can use them later
        self.pbr_extensions = default_pbr
        # e.g. self.pbr_extensions["roughness"] -> 0.5 by default
        # or user-specified if present

    def supports_shadow_mapping(self):
        return True

    def create_buffers(self):
        """
        Create buffers for each mesh material in the object's mesh list.

        This method iterates through each mesh in the object's mesh list and processes its materials.
        For each material, it extracts vertex data and performs transformations to reorder and enhance
        vertex attributes. The method constructs vertex buffer objects (VBOs) and vertex array objects
        (VAOs) for handling the vertex data in OpenGL. It accounts for tangents and bitangents calculations
        necessary for advanced shading techniques. The method appends created VBOs, VAOs, and a mapping
        relation for each material to the respective internal lists.

        Attributes
        ----------
        vaos : list
            A list to store vertex array objects for the processed meshes.
        vbos : list
            A list to store vertex buffer objects for the processed meshes.
        mesh_material_index_map : list
            A list to store the mapping between mesh index and material names for the
            processed materials.

        Parameters
        ----------
        self : object
            The instance of the object containing mesh_list attribute which holds
            the meshes to be processed.

        """
        self.vaos = []
        self.vbos = []
        self.mesh_material_index_map = []

        for mesh_index, mesh in enumerate(self.object.mesh_list):
            for material in mesh.materials:
                vertices = material.vertices
                if not vertices:
                    print(f"Material '{material.name}' in mesh '{mesh.name}' has no vertices. Skipping.")
                    continue

                # vertex_format: 'T2F_N3F_V3F' => uv(2), normal(3), position(3) = 8 floats total
                vertices_array = np.array(vertices, dtype=np.float32).reshape(-1, 8)

                # Current order: (u,v, nx,ny,nz, x,y,z)
                # Desired order: (x,y,z, nx,ny,nz, u,v)
                reordered = np.column_stack(
                    (
                        vertices_array[:, 5],  # x
                        vertices_array[:, 6],  # y
                        vertices_array[:, 7],  # z
                        vertices_array[:, 2],  # nx
                        vertices_array[:, 3],  # ny
                        vertices_array[:, 4],  # nz
                        vertices_array[:, 0],  # u
                        vertices_array[:, 1],  # v
                    )
                )

                # Compute tangents and bitangents
                reordered = self.compute_tangents_and_bitangents(reordered)

                # Now reordered has (x,y,z, nx,ny,nz, u,v, tx,ty,tz, bx,by,bz) = 14 floats/vertex
                vbo = self.create_vbo(reordered)
                vao = self.create_vao(with_tangents=True)

                self.vbos.append(vbo)
                self.vaos.append(vao)
                self.mesh_material_index_map.append((mesh_index, material.name))

    def compute_tangents_and_bitangents(self, verts):
        """
        Computes the tangent and bitangent vectors for a given set of vertices. The input
        vertices are expected to be in the format of N x 8 array, where each row consists
        of position (x, y, z), normal (nx, ny, nz), and texture coordinates (u, v). The
        method appends calculated tangent and bitangent vectors to each vertex, resulting
        in an output array of N x 14.

        Parameters:
            verts (np.ndarray): An array of shape (N, 8) containing vertices data which
                                include positions, normals, and texture coordinates.

        Returns:
            np.ndarray: An array of shape (N, 14), where each row is composed of the original
                        input data followed by calculated tangent (tx, ty, tz) and bitangent
                        (bx, by, bz) vectors.
        """
        # verts: N x 8: (x,y,z, nx,ny,nz, u,v)
        # We add tangent and bitangent: result N x 14
        tangent = np.zeros((verts.shape[0], 3), dtype=np.float32)
        bitangent = np.zeros((verts.shape[0], 3), dtype=np.float32)

        # Assume every 3 vertices form a triangle
        num_triangles = verts.shape[0] // 3
        for i in range(num_triangles):
            i0 = i * 3
            i1 = i * 3 + 1
            i2 = i * 3 + 2

            v0 = verts[i0]
            v1 = verts[i1]
            v2 = verts[i2]

            pos0 = v0[0:3]
            pos1 = v1[0:3]
            pos2 = v2[0:3]

            uv0 = v0[6:8]
            uv1 = v1[6:8]
            uv2 = v2[6:8]

            deltaPos1 = pos1 - pos0
            deltaPos2 = pos2 - pos0
            deltaUV1 = uv1 - uv0
            deltaUV2 = uv2 - uv0

            # Compute denominator for tangent calculation
            denom = deltaUV1[0] * deltaUV2[1] - deltaUV1[1] * deltaUV2[0]
            if abs(denom) < 1e-8:
                # Degenerate UV mapping, choose fallback tangent and bitangent
                # For fallback, pick a vector perpendicular to normal and another perpendicular to that.
                N = v0[3:6]
                # If N.z is not near 1, pick T along X:
                if abs(N[2]) < 0.9:
                    fallbackT = np.cross([0, 0, 1], N)
                else:
                    fallbackT = np.cross([0, 1, 0], N)
                if np.linalg.norm(fallbackT) < 1e-8:
                    fallbackT = [1, 0, 0]
                fallbackT = fallbackT / np.linalg.norm(fallbackT)

                fallbackB = np.cross(N, fallbackT)
                if np.linalg.norm(fallbackB) < 1e-8:
                    fallbackB = [0, 1, 0]

                T = fallbackT
                B = fallbackB
            else:
                r = 1.0 / denom
                T = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1]) * r
                B = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0]) * r

            # Add tangent/bitangent to all three vertices of the triangle
            tangent[i0] += T
            tangent[i1] += T
            tangent[i2] += T

            bitangent[i0] += B
            bitangent[i1] += B
            bitangent[i2] += B

        # Normalize and fix handedness
        for i in range(verts.shape[0]):
            N = verts[i, 3:6]
            T = tangent[i]
            B = bitangent[i]

            # Orthogonalize T against N
            T = T - N * np.dot(N, T)
            if np.linalg.norm(T) < 1e-8:
                # fallback T if needed
                # pick arbitrary perpendicular
                if abs(N[2]) < 0.9:
                    T = np.cross([0, 0, 1], N)
                else:
                    T = np.cross([0, 1, 0], N)
            T = T / np.linalg.norm(T)

            # Orthogonalize B
            B = B - N * np.dot(N, B) - T * np.dot(T, B)
            if np.linalg.norm(B) < 1e-8:
                # fallback B if needed
                B = np.cross(N, T)
                if np.linalg.norm(B) < 1e-8:
                    B = [0, 1, 0]
            B = B / np.linalg.norm(B)

            # Enforce consistent handedness
            # If cross(N, T) dot B < 0, invert B
            handedness = np.dot(np.cross(N, T), B)
            if handedness < 0.0:
                B = -B

            tangent[i] = T
            bitangent[i] = B

        final_array = np.hstack((verts, tangent, bitangent)).astype(np.float32)
        return final_array

    def create_vbo(self, vertices_array):
        """
        Creates a Vertex Buffer Object (VBO) using the provided array of vertices.
        The VBO is generated, bound to the GL_ARRAY_BUFFER target, and loaded
        with the vertex data from the given array. The data is specified to be
        static and drawn frequently.

        Parameters:
            vertices_array: numpy.ndarray
                An array of vertex data used to populate the VBO.

        Returns:
            int: An integer representing the generated VBO handle.
        """
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self, with_tangents=False):
        """
        Creates a Vertex Array Object (VAO) and sets up vertex attributes for
        rendering. The attributes can include position, normal, texture coordinates,
        and optionally tangent and bitangent vectors if specified.

        The method initializes a new VAO, binds it, and then retrieves attribute
        locations from the shader program. It enables vertex attributes based on
        whether tangents are included or not, with specific offsets for each type
        of attribute data within the vertex layout.

        Parameters:
        with_tangents: bool
            Flag indicating whether tangent and bitangent attributes should be
            included in the vertex layout. If True, the VAO includes these
            attributes; otherwise, it does not.

        Returns:
        int
            The ID of the created VAO used for rendering operations.
        """
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        if with_tangents:
            # (x,y,z, nx,ny,nz, u,v, tx,ty,tz, bx,by,bz) = 14 floats
            vertex_stride = 14 * self.float_size
        else:
            # Without tangents, we had 8 floats
            vertex_stride = 8 * self.float_size

        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        # Position: (x,y,z) at offset 0
        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 0)
        # Normal: (nx,ny,nz) at offset 3 floats
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 3 * self.float_size)
        # UV: (u,v) at offset 6 floats
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 6 * self.float_size)
        if with_tangents:
            # Tangent: at offset 8 floats
            if tangent_loc >= 0:
                self.enable_vertex_attrib(tangent_loc, 3, vertex_stride, 8 * self.float_size)
            # Bitangent: at offset 11 floats
            if bitangent_loc >= 0:
                self.enable_vertex_attrib(bitangent_loc, 3, vertex_stride, 11 * self.float_size)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        return vao

    def get_vertex_stride(self, vertex_format):
        """
        Calculate the total vertex stride from a given vertex format.

        The method parses the input vertex format string, which is expected to be
        composed of parts separated by underscores, with each part containing a
        single character specification followed by an integer. The integer indicates
        the number of floats in that portion of the vertex. It totals these numbers
        to compute the total stride count.

        Args:
            vertex_format (str): A string representing the format of the vertex.

        Returns:
            int: The total vertex stride calculated from the format.
        """
        count = 0
        format_parts = vertex_format.split("_")
        for part in format_parts:
            num = int(part[1])  # number of floats
            count += num
        return count

    def enable_vertex_attrib(self, location, size, stride, pointer_offset):
        """
        Enables a vertex attribute array and defines an array of generic vertex
        attribute data. This function is primarily used in OpenGL to specify the
        organization of data in the vertex buffer and to pass it to the vertex
        shader.

        Parameters:
        location (int): The location of the vertex attribute to be enabled.
        size (int): The number of components per attribute. Must be 1, 2, 3, or 4.
        stride (int): The byte offset between consecutive vertex attributes.
        pointer_offset (int): The offset of the first component of the first
        generic vertex attribute in the buffer.
        """
        if location >= 0:
            glEnableVertexAttribArray(location)
            glVertexAttribPointer(location, size, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(pointer_offset))

    @common_funcs
    def render(self):
        """
        Render all meshes of the object with their corresponding materials.

        This method iterates over each mesh in the object's mesh list. For each
        material in the mesh, it checks if the material has associated vertices. If
        vertices are present, it applies the material to the context and calculates
        the number of vertices to draw based on the vertex stride of the material.
        Then, it binds and draws the vertex array object for that material. The
        vao_counter is incremented after each draw call to ensure uniqueness for
        each material's vertex array object.

        Raises:
            Any exceptions pertaining to applying material or drawing a vertex
            array may be raised during execution.
        """
        vao_counter = 0
        for mesh_index, mesh in enumerate(self.object.mesh_list):
            for material in mesh.materials:
                vertices = material.vertices
                if not vertices:
                    continue

                # 1) Set the material uniforms before drawing
                self.apply_material(material)

                # 2) Figure out how many vertices this material uses
                count = len(vertices) // self.get_vertex_stride(material.vertex_format)

                # 3) Bind and draw
                self.bind_and_draw_vao(vao_counter, count)
                vao_counter += 1

    def apply_material(self, material):
        """
        Sets all the fields of our extended 'Material' struct in GLSL,
        based on what pywavefront loads. If any fields are missing, we
        provide a default fallback.
        """
        glUseProgram(self.shader_engine.shader_program)

        """
        # Material Parameter Legend and Descriptions

        ## Basic Fields (handled by pywavefront)
        1. `ambient` (`Ka` in .mtl)
           - Description: The ambient reflectivity of the material. Defines the color under ambient light.
           - Typical Range: RGB values (0.0–1.0).

        2. `diffuse` (`Kd` in .mtl)
           - Description: The diffuse reflectivity of the material. Defines how the material reflects light diffusely.
           - Typical Range: RGB values (0.0–1.0).

        3. `specular` (`Ks` in .mtl)
           - Description: The specular reflectivity of the material. Defines the color of the specular highlights.
           - Typical Range: RGB values (0.0–1.0).

        4. `shininess` (`Ns` in .mtl)
           - Description: The specular exponent, controlling the size and sharpness of specular highlights.
           - Typical Range: Float (0–1000; clamped in shaders).

        5. `transparency` (`d` in .mtl)
           - Description: The transparency (or alpha) of the material. `1.0` is opaque, `0.0` is fully transparent.
           - Typical Range: Float (0.0–1.0).
           - Note: Pywavefront provides `transparency` directly, which is equivalent to `d` in .mtl.

        6. `ior` (`Ni` in .mtl)
           - Description: The index of refraction for transparent materials, like glass.
           - Typical Range: Float (>1.0; e.g., 1.45 for glass).

        7. `emissive` (`Ke` in .mtl)
           - Description: The emissive color of the material. Acts as if the material emits light.
           - Typical Range: RGB values (0.0–1.0).

        8. `illumination_model` (`illum` in .mtl)
           - Description: Specifies the lighting model:
             - `0`: Color only, no shading.
             - `1`: Diffuse shading only.
             - `2`: Diffuse + specular highlights.
           - Typical Range: Integer.

        ---

        ## PBR Extensions (NOT handled by pywavefront; must be added manually)
        9. `roughness` (`Pr` in Blender .mtl)
           - Description: Controls surface roughness. Low values result in smooth, shiny surfaces; high values create rough, diffuse surfaces.
           - Typical Range: Float (0.0–1.0).
           - Default: 0.5 (fallback).

        10. `metallic` (`Pm` in Blender .mtl)
            - Description: Defines whether the material behaves like a metal (1.0) or a dielectric (0.0).
            - Typical Range: Float (0.0–1.0).
            - Default: 0.0 (fallback).

        11. `clearcoat` (`Pc` in Blender .mtl)
            - Description: Adds a reflective clearcoat layer to the material.
            - Typical Range: Float (0.0–1.0).
            - Default: 0.0 (fallback).

        12. `clearcoatRoughness` (`Pcr` in Blender .mtl)
            - Description: Controls the roughness of the clearcoat layer.
            - Typical Range: Float (0.0–1.0).
            - Default: 0.03 (fallback).

        13. `sheen` (`Ps` in Blender .mtl)
            - Description: Simulates soft, fuzzy reflections for materials like velvet.
            - Typical Range: Float (0.0–1.0).
            - Default: 0.0 (fallback).

        14. `anisotropy` (`aniso` in Blender .mtl)
            - Description: Simulates directional reflections, such as brushed metal.
            - Typical Range: Float (-1.0 to 1.0).
            - Default: 0.0 (fallback).

        15. `anisotropyRot` (`anisor` in Blender .mtl)
            - Description: Rotates the anisotropic reflection pattern.
            - Typical Range: Float (0.0–1.0).
            - Default: 0.0 (fallback).

        ---

        ## Notes
        - Pywavefront handles basic fields (`ambient`, `diffuse`, `specular`, `shininess`, `transparency`, `ior`, `emissive`, `illumination_model`).
        - PBR extensions (`roughness`, `metallic`, `clearcoat`, etc.) are NOT parsed by pywavefront and must be added manually via custom configuration.
        - Defaults are provided for PBR extensions if they are not explicitly set.
        """

        ############################################
        # 1) Retrieve uniform locations for each field
        ############################################
        # We'll prefix them with "material." since the GLSL struct is named `Material material;`
        loc_ambient = glGetUniformLocation(self.shader_engine.shader_program, "material.ambient")
        loc_diffuse = glGetUniformLocation(self.shader_engine.shader_program, "material.diffuse")
        loc_specular = glGetUniformLocation(self.shader_engine.shader_program, "material.specular")
        loc_shininess = glGetUniformLocation(self.shader_engine.shader_program, "material.shininess")

        # Get the uniform locations for your material struct fields
        loc_roughness = glGetUniformLocation(self.shader_engine.shader_program, "material.roughness")
        loc_metallic = glGetUniformLocation(self.shader_engine.shader_program, "material.metallic")

        loc_ior = glGetUniformLocation(self.shader_engine.shader_program, "material.ior")
        loc_emissive = glGetUniformLocation(self.shader_engine.shader_program, "material.emissive")
        loc_illumination_model = glGetUniformLocation(self.shader_engine.shader_program, "material.illuminationModel")
        loc_transparency = glGetUniformLocation(self.shader_engine.shader_program, "material.transparency")
        loc_clearcoat = glGetUniformLocation(self.shader_engine.shader_program, "material.clearcoat")
        loc_clearcoat_roughness = glGetUniformLocation(self.shader_engine.shader_program, "material.clearcoatRoughness")
        loc_sheen = glGetUniformLocation(self.shader_engine.shader_program, "material.sheen")
        loc_anisotropy = glGetUniformLocation(self.shader_engine.shader_program, "material.anisotropy")
        loc_anisotropy_rot = glGetUniformLocation(self.shader_engine.shader_program, "material.anisotropyRot")
        loc_transmission = glGetUniformLocation(self.shader_engine.shader_program, "material.transmission")

        # The standard fields from pywavefront
        ambient = getattr(material, "ambient", [0.2, 0.2, 0.2, 1.0])[:3]
        diffuse = getattr(material, "diffuse", [0.8, 0.8, 0.8, 1.0])[:3]
        specular = getattr(material, "specular", [0.5, 0.5, 0.5, 1.0])[:3]
        shininess = getattr(material, "shininess", 32.0)
        ior = getattr(material, "optical_density", 1.0)
        emissive = getattr(material, "emissive", [0.0, 0.0, 0.0, 1.0])[:3]
        illumination_model = getattr(material, "illumination_model", 2)
        transparency = getattr(material, "transparency", 1.0)

        # Now for the pbr_extensions. If no user override was given, use a default.
        roughness = self.pbr_extensions.get("roughness", 0.5)  # Default: 0.5 (moderately rough surface)
        metallic = self.pbr_extensions.get("metallic", 0.0)  # Default: 0.0 (non-metallic)
        clearcoat = self.pbr_extensions.get("clearcoat", 0.0)  # Default: 0.0 (no clearcoat)
        clearcoat_roughness = self.pbr_extensions.get("clearcoat_roughness",
                                                      0.5)  # Default: 0.5 (average roughness for clearcoat)
        sheen = self.pbr_extensions.get("sheen", 0.0)  # Default: 0.0 (no sheen)
        aniso = self.pbr_extensions.get("aniso", 0.0)  # Default: 0.0 (no anisotropy)
        anisor = self.pbr_extensions.get("anisor", 0.0)  # Default: 0.0 (no anisotropic rotation)
        transmission = self.pbr_extensions.get("transmission", (0.0, 0.0, 0.0))  # Default: 0.0 (no transparency)

        ############################################
        # 3) Upload each to GPU
        ############################################
        if loc_ambient >= 0:
            glUniform3f(loc_ambient, *ambient)
        if loc_diffuse >= 0:
            glUniform3f(loc_diffuse, *diffuse)
        if loc_specular >= 0:
            glUniform3f(loc_specular, *specular)
        if loc_shininess >= 0:
            glUniform1f(loc_shininess, shininess)

        if loc_roughness >= 0:
            glUniform1f(loc_roughness, roughness)
        if loc_metallic >= 0:
            glUniform1f(loc_metallic, metallic)

        if loc_ior >= 0:
            glUniform1f(loc_ior, float(ior))
        if loc_emissive >= 0:
            glUniform3f(loc_emissive, *emissive)
        if loc_illumination_model >= 0:
            glUniform1i(loc_illumination_model, illumination_model)
        if loc_transparency >= 0:
            glUniform1f(loc_transparency, float(transparency))
        if loc_clearcoat >= 0:
            glUniform1f(loc_clearcoat, clearcoat)
        if loc_clearcoat_roughness >= 0:
            glUniform1f(loc_clearcoat_roughness, clearcoat_roughness)
        if loc_sheen >= 0:
            glUniform1f(loc_sheen, sheen)
        if loc_anisotropy >= 0:
            glUniform1f(loc_anisotropy, aniso)
        if loc_anisotropy_rot >= 0:
            glUniform1f(loc_anisotropy_rot, anisor)
        if loc_transmission >= 0:
            glUniform3f(loc_transmission, *transmission)

    def bind_and_draw_vao(self, vao_index, count):
        """
        Binds a Vertex Array Object (VAO) and issues a draw call for rendering.

        This method activates a specific VAO from a list of VAOs and performs a
        drawing operation using OpenGL's glDrawArrays function. After drawing,
        it unbinds the VAO. This is typically used in rendering pipelines
        where objects are drawn using vertex data stored in a VAO.

        Parameters:
            vao_index: int
                The index of the VAO to bind from the list of available VAOs.
            count: int
                The number of vertices to render.
        """
        glBindVertexArray(self.vaos[vao_index])
        glDrawArrays(GL_TRIANGLES, 0, count)
        glBindVertexArray(0)

    def shutdown(self):
        if hasattr(self, "vaos") and len(self.vaos) > 0:
            glDeleteVertexArrays(len(self.vaos), self.vaos)

        if hasattr(self, "vbos") and len(self.vbos) > 0:
            glDeleteBuffers(len(self.vbos), self.vbos)

        if hasattr(self, "ebos") and len(self.ebos) > 0:
            glDeleteBuffers(len(self.ebos), self.ebos)

        self.shader_engine.delete_shader_programs()
