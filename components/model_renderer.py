# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import os

import numpy as np
import pywavefront
from OpenGL.GL import *

from components.abstract_renderer import AbstractRenderer, with_gl_render_state
from components.texture_manager import TextureManager

# ------------------------------------------------------------------------------
# Global Variables / Managers
# ------------------------------------------------------------------------------
texture_manager = TextureManager()


# ------------------------------------------------------------------------------
# Helper Functions: PBR Extensions Parsing
# ------------------------------------------------------------------------------
def parse_pbr_extensions_from_mtl(mtl_path):
    """
    Parse extra PBR lines in a .mtl file, returning a dict of dicts:
        {
            'MaterialName': {
                'Pr': 0.399083,
                'Pm': 0.064220,
                'Ps': 0.036697,
                'Pc': 0.110092,
                'Pcr': 0.039174,
                'aniso': 0.036697,
                'anisor': 0.036697,
                'Tf': (0.027523, 0.027523, 0.027523),
                'Pfe': 0.5,
                ...
            },
            'AnotherMaterial': { ... }
        }
    It looks specifically for tokens like Pr, Pm, Ps, Pc, Pcr, aniso, anisor, Tf, etc.
    If the file or lines are missing, it returns an empty dict or partial data.
    """
    pbr_data_by_material = {}
    current_mat_name = None

    # Tokens to expect
    single_float_tokens = {"Pr", "Pm", "Ps", "Pc", "Pcr", "aniso", "anisor", "Pfe"}
    triple_float_tokens = {"Tf"}

    if not os.path.isfile(mtl_path):
        print(f"[parse_pbr_extensions_from_mtl] No .mtl file found at: {mtl_path}")
        return pbr_data_by_material

    with open(mtl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("newmtl "):
                current_mat_name = line.split(None, 1)[1]
                if current_mat_name not in pbr_data_by_material:
                    pbr_data_by_material[current_mat_name] = {}
                continue
            if not current_mat_name:
                continue
            parts = line.split()
            if not parts:
                continue
            token = parts[0]
            if token in single_float_tokens:
                try:
                    value = float(parts[1])
                    pbr_data_by_material[current_mat_name][token] = value
                except (IndexError, ValueError):
                    pass
            elif token in triple_float_tokens:
                try:
                    x = float(parts[1])
                    y = float(parts[2])
                    z = float(parts[3])
                    pbr_data_by_material[current_mat_name][token] = (x, y, z)
                except (IndexError, ValueError):
                    pass

    return pbr_data_by_material


# ------------------------------------------------------------------------------
# Helper Functions: Upload Material Uniforms
# ------------------------------------------------------------------------------
def upload_material_uniforms(shader_program, material, fallback_pbr):
    """
    Upload material uniforms to the GPU. If any expected uniform is not found,
    raise a RuntimeError listing the missing uniforms.

    Parameters:
        shader_program (int): The OpenGL shader program handle.
        material: The pywavefront material object.
        fallback_pbr (dict): A dictionary containing fallback PBR parameters.
    """
    uniform_names = {
        "material.specular": "specular",
        "material.ior": "ior",
        "material.emissive": "emissive",
        "material.illuminationModel": "illumination_model",
        "material.roughness": "roughness",
        "material.metallic": "metallic",
        "material.clearcoat": "clearcoat",
        "material.clearcoatRoughness": "clearcoat_roughness",
        "material.sheen": "sheen",
        "material.transmission": "transmission",
        "material.fresnelExponent": "fresnel_exponent",
    }

    # Retrieve standard material properties from the material (with defaults)
    ambient = getattr(material, "ambient", [0.2, 0.2, 0.2, 1.0])[:3]
    diffuse = getattr(material, "diffuse", [0.8, 0.8, 0.8, 1.0])[:3]
    specular = getattr(material, "specular", [0.5, 0.5, 0.5, 1.0])[:3]
    ior = getattr(material, "optical_density", 1.0)
    emissive = getattr(material, "emissive", [0.0, 0.0, 0.0, 1.0])[:3]
    illumination_model = getattr(material, "illumination_model", 2)
    transparency = getattr(material, "transparency", 1.0)

    # Merge fallback PBR parameters with any extra PBR data from the material
    local_pbr = dict(fallback_pbr)
    mat_pbr = getattr(material, "pbr_extensions", {})
    if "Pr" in mat_pbr:
        local_pbr["roughness"] = mat_pbr["Pr"]
    if "Pm" in mat_pbr:
        local_pbr["metallic"] = mat_pbr["Pm"]
    if "Pc" in mat_pbr:
        local_pbr["clearcoat"] = mat_pbr["Pc"]
    if "Pcr" in mat_pbr:
        local_pbr["clearcoat_roughness"] = mat_pbr["Pcr"]
    if "Ps" in mat_pbr:
        local_pbr["sheen"] = mat_pbr["Ps"]
    if "aniso" in mat_pbr:
        local_pbr["anisotropy"] = mat_pbr["aniso"]
    if "anisor" in mat_pbr:
        local_pbr["anisotropy_rot"] = mat_pbr["anisor"]
    if "Tf" in mat_pbr:
        local_pbr["transmission"] = mat_pbr["Tf"]
    if "Pfe" in mat_pbr:
        local_pbr["fresnel_exponent"] = mat_pbr["Pfe"]

    roughness = local_pbr.get("roughness", 0.5)
    metallic = local_pbr.get("metallic", 0.0)
    clearcoat = local_pbr.get("clearcoat", 0.0)
    clearcoat_roughness = local_pbr.get("clearcoat_roughness", 0.03)
    sheen = local_pbr.get("sheen", 0.0)
    anisotropy = local_pbr.get("anisotropy", 0.0)
    anisotropy_rot = local_pbr.get("anisotropy_rot", 0.0)
    transmission = local_pbr.get("transmission", (0.0, 0.0, 0.0))
    fresnel_exponent = local_pbr.get("fresnel_exponent", 0.5)

    material_values = {
        "ambient": ambient,
        "diffuse": diffuse,
        "specular": specular,
        "ior": ior,
        "emissive": emissive,
        "illumination_model": illumination_model,
        "transparency": transparency,
        "roughness": roughness,
        "metallic": metallic,
        "clearcoat": clearcoat,
        "clearcoat_roughness": clearcoat_roughness,
        "sheen": sheen,
        "anisotropy": anisotropy,
        "anisotropy_rot": anisotropy_rot,
        "transmission": transmission,
        "fresnel_exponent": fresnel_exponent,
    }

    uniform_locations = {}
    missing_uniforms = []
    for uniform_name, key in uniform_names.items():
        loc = glGetUniformLocation(shader_program, uniform_name)
        uniform_locations[uniform_name] = loc
        if loc == -1:
            missing_uniforms.append(uniform_name)
    if missing_uniforms:
        raise RuntimeError("Uniform(s) not found in shader program: " + ", ".join(missing_uniforms))

    glUniform3f(uniform_locations["material.specular"], *material_values["specular"])
    glUniform1f(uniform_locations["material.ior"], float(material_values["ior"]))
    glUniform3f(uniform_locations["material.emissive"], *material_values["emissive"])
    glUniform1i(uniform_locations["material.illuminationModel"], int(material_values["illumination_model"]))
    glUniform1f(uniform_locations["material.roughness"], material_values["roughness"])
    glUniform1f(uniform_locations["material.metallic"], material_values["metallic"])
    glUniform1f(uniform_locations["material.clearcoat"], material_values["clearcoat"])
    glUniform1f(uniform_locations["material.clearcoatRoughness"], material_values["clearcoat_roughness"])
    glUniform1f(uniform_locations["material.sheen"], material_values["sheen"])
    glUniform3f(uniform_locations["material.transmission"], *material_values["transmission"])
    glUniform1f(uniform_locations["material.fresnelExponent"], material_values["fresnel_exponent"])


# ------------------------------------------------------------------------------
# ModelRenderer Class
# ------------------------------------------------------------------------------
class ModelRenderer(AbstractRenderer):
    def __init__(self, renderer_name, obj_path, **kwargs):
        """
        Initialize the ModelRenderer.

        Loads the .obj file (with materials and faces), parses any extra PBR data
        from the corresponding .mtl file, and applies user-provided PBR overrides.
        """
        super().__init__(renderer_name=renderer_name, **kwargs)
        self.obj_path = obj_path

        # Load the .obj file with materials and face data
        self.object = pywavefront.Wavefront(self.obj_path, create_materials=True, collect_faces=True)

        # Attempt to parse the corresponding .mtl for extra PBR extensions
        mtl_path = self.obj_path.replace(".obj", ".mtl")
        extra_pbr_data = parse_pbr_extensions_from_mtl(mtl_path)

        # Attach extra PBR data to each material
        for mesh in self.object.mesh_list:
            for mat in mesh.materials:
                mat_name = getattr(mat, "name", None)
                if mat_name and mat_name in extra_pbr_data:
                    mat.pbr_extensions = extra_pbr_data[mat_name]
                else:
                    mat.pbr_extensions = {}

        # Process user override PBR parameters
        override_pbr = kwargs.get("pbr_extension_overrides") or {}
        friendly_to_token = {
            "roughness": "Pr",
            "metallic": "Pm",
            "clearcoat": "Pc",
            "clearcoat_roughness": "Pcr",
            "sheen": "Ps",
            "anisotropy": "aniso",
            "anisotropy_rot": "anisor",
            "transmission": "Tf",
            "fresnel_exponent": "Pfe",
        }
        allowed_keys = set(friendly_to_token.keys())
        invalid_keys = [key for key in override_pbr if key not in allowed_keys]
        if invalid_keys:
            raise ValueError(
                "No such material property: "
                + ", ".join(invalid_keys)
                + "; available pbr overrides are: "
                + ", ".join(sorted(allowed_keys))
            )
        for mesh in self.object.mesh_list:
            for mat in mesh.materials:
                for friendly, token in friendly_to_token.items():
                    if friendly in override_pbr:
                        mat.pbr_extensions[token] = override_pbr[friendly]

        # Create fallback PBR parameters
        default_pbr = {
            "roughness": 0.5,
            "metallic": 0.0,
            "clearcoat": 0.0,
            "clearcoat_roughness": 0.03,
            "sheen": 0.0,
            "aniso": 0.0,
            "anisor": 0.0,
            "transmission": (0.0, 0.0, 0.0),
            "fresnel_exponent": 0.5,
        }
        default_pbr.update(override_pbr)
        self.pbr_extension_overrides = default_pbr

    # --------------------------------------------------------------------------
    # Shadow Mapping Support
    # --------------------------------------------------------------------------
    def supports_shadow_mapping(self):
        return True

    # --------------------------------------------------------------------------
    # Buffer Creation
    # --------------------------------------------------------------------------
    def create_buffers(self):
        """
        Create buffers (VBOs and VAOs) for each material in every mesh.
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

                vertices_array = np.array(vertices, dtype=np.float32).reshape(-1, 8)
                # Reorder the vertex components:
                #   [x, y, z, nx, ny, nz, u, v] -> [x, y, z, nx, ny, nz, u, v]
                # But here, reordering is performed as follows:
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
                # Compute tangent and bitangent vectors and append them
                reordered = self.compute_tangents_and_bitangents(reordered)
                vbo = self.create_vbo(reordered)
                vao = self.create_vao(with_tangents=True)
                self.vbos.append(vbo)
                self.vaos.append(vao)
                self.mesh_material_index_map.append((mesh_index, material.name))

    def compute_tangents_and_bitangents(self, verts):
        """
        Compute tangent and bitangent vectors for an N x 8 array of vertices.
        Returns an N x 14 array with appended tangent and bitangent vectors.
        """
        tangent = np.zeros((verts.shape[0], 3), dtype=np.float32)
        bitangent = np.zeros((verts.shape[0], 3), dtype=np.float32)
        num_triangles = verts.shape[0] // 3

        for i in range(num_triangles):
            i0, i1, i2 = i * 3, i * 3 + 1, i * 3 + 2
            v0, v1, v2 = verts[i0], verts[i1], verts[i2]
            pos0, pos1, pos2 = v0[0:3], v1[0:3], v2[0:3]
            uv0, uv1, uv2 = v0[6:8], v1[6:8], v2[6:8]
            deltaPos1 = pos1 - pos0
            deltaPos2 = pos2 - pos0
            deltaUV1 = uv1 - uv0
            deltaUV2 = uv2 - uv0

            denom = deltaUV1[0] * deltaUV2[1] - deltaUV1[1] * deltaUV2[0]
            if abs(denom) < 1e-8:
                N = v0[3:6]
                fallbackT = np.cross([0, 0, 1], N) if abs(N[2]) < 0.9 else np.cross([0, 1, 0], N)
                if np.linalg.norm(fallbackT) < 1e-8:
                    fallbackT = [1, 0, 0]
                fallbackT = fallbackT / np.linalg.norm(fallbackT)
                fallbackB = np.cross(N, fallbackT)
                if np.linalg.norm(fallbackB) < 1e-8:
                    fallbackB = [0, 1, 0]
                T, B = fallbackT, fallbackB
            else:
                r = 1.0 / denom
                T = (deltaPos1 * deltaUV2[1] - deltaPos2 * deltaUV1[1]) * r
                B = (deltaPos2 * deltaUV1[0] - deltaPos1 * deltaUV2[0]) * r

            tangent[i0] += T
            tangent[i1] += T
            tangent[i2] += T
            bitangent[i0] += B
            bitangent[i1] += B
            bitangent[i2] += B

        for i in range(verts.shape[0]):
            N = verts[i, 3:6]
            T = tangent[i]
            B = bitangent[i]
            T = T - N * np.dot(N, T)
            if np.linalg.norm(T) < 1e-8:
                T = np.cross([0, 0, 1], N) if abs(N[2]) < 0.9 else np.cross([0, 1, 0], N)
            T = T / np.linalg.norm(T)
            B = B - N * np.dot(N, B) - T * np.dot(T, B)
            if np.linalg.norm(B) < 1e-8:
                B = np.cross(N, T)
                if np.linalg.norm(B) < 1e-8:
                    B = [0, 1, 0]
            B = B / np.linalg.norm(B)
            if np.dot(np.cross(N, T), B) < 0.0:
                B = -B
            tangent[i] = T
            bitangent[i] = B

        final_array = np.hstack((verts, tangent, bitangent)).astype(np.float32)
        return final_array

    def create_vbo(self, vertices_array):
        """
        Create and bind a Vertex Buffer Object (VBO) for the given vertex array.
        """
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices_array.nbytes, vertices_array, GL_STATIC_DRAW)
        return vbo

    def create_vao(self, with_tangents=False):
        """
        Create and set up a Vertex Array Object (VAO) with optional tangent/bitangent attributes.
        """
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        vertex_stride = 14 * self.float_size if with_tangents else 8 * self.float_size

        position_loc = glGetAttribLocation(self.shader_engine.shader_program, "position")
        normal_loc = glGetAttribLocation(self.shader_engine.shader_program, "normal")
        tex_coords_loc = glGetAttribLocation(self.shader_engine.shader_program, "texCoords")
        tangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "tangent")
        bitangent_loc = glGetAttribLocation(self.shader_engine.shader_program, "bitangent")

        if position_loc >= 0:
            self.enable_vertex_attrib(position_loc, 3, vertex_stride, 0)
        if normal_loc >= 0:
            self.enable_vertex_attrib(normal_loc, 3, vertex_stride, 3 * self.float_size)
        if tex_coords_loc >= 0:
            self.enable_vertex_attrib(tex_coords_loc, 2, vertex_stride, 6 * self.float_size)
        if with_tangents:
            if tangent_loc >= 0:
                self.enable_vertex_attrib(tangent_loc, 3, vertex_stride, 8 * self.float_size)
            if bitangent_loc >= 0:
                self.enable_vertex_attrib(bitangent_loc, 3, vertex_stride, 11 * self.float_size)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)
        return vao

    def get_vertex_stride(self, vertex_format):
        """
        Compute the vertex stride (number of components) from the vertex format string.
        """
        count = 0
        for part in vertex_format.split("_"):
            count += int(part[1])
        return count

    def enable_vertex_attrib(self, location, size, stride, pointer_offset):
        """
        Enable and set the vertex attribute pointer.
        """
        if location >= 0:
            glEnableVertexAttribArray(location)
            glVertexAttribPointer(location, size, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(pointer_offset))

    # --------------------------------------------------------------------------
    # Rendering Methods
    # --------------------------------------------------------------------------
    @with_gl_render_state
    def render(self):
        """
        Render all meshes of the object using their corresponding materials.
        """
        vao_counter = 0
        for mesh_index, mesh in enumerate(self.object.mesh_list):
            for material in mesh.materials:
                vertices = material.vertices
                if not vertices:
                    continue
                self.apply_material(material)
                count = len(vertices) // self.get_vertex_stride(material.vertex_format)
                self.bind_and_draw_vao(vao_counter, count)
                vao_counter += 1

    def apply_material(self, material):
        """
        Upload the material uniforms to the GPU.
        """
        glUseProgram(self.shader_engine.shader_program)
        upload_material_uniforms(self.shader_engine.shader_program, material, self.pbr_extension_overrides)

    def bind_and_draw_vao(self, vao_index, count):
        """
        Bind the VAO at the given index and issue the draw call.
        """
        glBindVertexArray(self.vaos[vao_index])
        glDrawArrays(GL_TRIANGLES, 0, count)
        glBindVertexArray(0)

    # --------------------------------------------------------------------------
    # Shutdown and Resource Cleanup
    # --------------------------------------------------------------------------
    def shutdown(self):
        """
        Clean up allocated OpenGL resources.
        """
        if hasattr(self, "vaos") and self.vaos:
            glDeleteVertexArrays(len(self.vaos), self.vaos)
        if hasattr(self, "vbos") and self.vbos:
            glDeleteBuffers(len(self.vbos), self.vbos)
        if hasattr(self, "ebos") and self.ebos:
            glDeleteBuffers(len(self.ebos), self.ebos)
        self.shader_engine.delete_shader_programs()
