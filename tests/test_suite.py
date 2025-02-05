"""
test_suite.py

This module contains a suite of unit tests for many components of your 3D rendering
benchmarking system. To avoid errors when no OpenGL context or shader folder is present,
we override some methods (e.g. discover_shaders) and patch OpenGL functions.
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

# Adjust the Python path so that modules from your project can be imported.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import modules from your project.
from components.renderer_config import RendererConfig
from components.audio_player import AudioPlayer
from components.benchmark_manager import BenchmarkManager
from components.camera_control import CameraController
from components.scene_constructor import SceneConstructor
from components.shader_engine import ShaderEngine
from components.shadow_map_manager import ShadowMapManager
from components.stats_collector import StatsCollector
from components.texture_manager import TextureManager
from components.surface_renderer import SurfaceRenderer
from components.skybox_renderer import SkyboxRenderer
from components.renderer_instancing import RenderingInstance
from components.abstract_renderer import AbstractRenderer

# --- Global override for shader discovery ---
# When running tests, we don’t have a valid "shaders" folder.
RendererConfig.discover_shaders = lambda self: None

# --- Dummy Classes for Testing --- #

class DummyRenderer(AbstractRenderer):
    """
    A simple concrete subclass of AbstractRenderer for testing.
    It records when create_buffers() and render() are called.
    """
    def __init__(self, renderer_name):
        # Supply a dummy shader_names dictionary so that AbstractRenderer is properly initialized.
        super().__init__(renderer_name=renderer_name, shader_names={"vertex": "dummy", "fragment": "dummy"})
        self.buffers_created = False
        self.render_called = False

    def create_buffers(self):
        self.buffers_created = True

    def render(self):
        self.render_called = True

class DummySurfaceRenderer(SurfaceRenderer):
    def __init__(self, renderer_name, **kwargs):
        # Supply dummy shader_names.
        super().__init__(renderer_name=renderer_name, shader_names={"vertex": "dummy", "fragment": "dummy"}, **kwargs)
    def create_buffers(self):
        pass
    def render(self):
        pass

class DummySkyboxRenderer(SkyboxRenderer):
    def __init__(self, renderer_name, **kwargs):
        super().__init__(renderer_name=renderer_name, shader_names={"vertex": "dummy", "fragment": "dummy"}, **kwargs)
    def create_buffers(self):
        # For testing, simply generate dummy vertices.
        self.vertices = [0.0] * 36
    def render(self):
        pass


# --- Dummy run function for BenchmarkManager ---
def dummy_run_function(stats_queue, stop_event, resolution, msaa_level, anisotropy, shading_model,
                       shadow_map_resolution, particle_render_mode, vsync_enabled, sound_enabled, fullscreen):
    if stats_queue is not None:
        stats_queue.put(("ready", None))
        stats_queue.put(("fps", 60))
    time.sleep(0.1)


# --- Dummy play_audio for AudioPlayer ---
def dummy_play_audio(self):
    # Simulate that audio is playing until stop_event is set.
    self.is_playing.set()
    self.stop_event.wait(timeout=1)
    self.is_playing.clear()

# --- Test Classes --- #

class TestRendererConfig(unittest.TestCase):
    """Tests for RendererConfig and its add_* methods."""
    def setUp(self):
        # The discover_shaders method is already overridden globally.
        self.config = RendererConfig(window_title="TestRenderer", window_size=(800, 600))

    def test_add_model_returns_valid_config(self):
        model_config = self.config.add_model(
            obj_path="dummy.obj",
            texture_paths={"diffuse": "dummy.png"},
            shader_names=("standard", "default")
        )
        self.assertIsInstance(model_config, dict)
        self.assertEqual(model_config.get("obj_path"), "dummy.obj")
        self.assertEqual(model_config.get("texture_paths"), {"diffuse": "dummy.png"})
        self.assertEqual(model_config.get("shader_names"), ("standard", "default"))

    def test_add_surface_returns_valid_config(self):
        surface_config = self.config.add_surface(shader_names=("surface_vertex", "surface_fragment"))
        self.assertIsInstance(surface_config, dict)
        self.assertEqual(surface_config.get("shader_names"), ("surface_vertex", "surface_fragment"))

    def test_add_skybox_returns_valid_config(self):
        skybox_config = self.config.add_skybox(
            cubemap_folder="dummy_cube", shader_names=("skybox_vertex", "skybox_fragment")
        )
        self.assertIsInstance(skybox_config, dict)
        self.assertEqual(skybox_config.get("cubemap_folder"), "dummy_cube")
        self.assertEqual(skybox_config.get("shader_names"), ("skybox_vertex", "skybox_fragment"))

    def test_add_particle_renderer_returns_valid_config(self):
        particle_config = self.config.add_particle_renderer(
            particle_render_mode="cpu", shader_names=("particle_vertex", "particle_fragment")
        )
        self.assertIsInstance(particle_config, dict)
        self.assertEqual(particle_config.get("particle_render_mode"), "cpu")
        self.assertEqual(particle_config.get("shader_names"), ("particle_vertex", "particle_fragment"))

class TestAudioPlayer(unittest.TestCase):
    """Tests for the AudioPlayer class."""

    @patch.object(AudioPlayer, "play_audio", new=dummy_play_audio)
    @patch("pygame.mixer.init")
    @patch("pygame.mixer.music.load")
    @patch("pygame.mixer.music.play")
    @patch("pygame.mixer.music.stop")
    @patch("pygame.mixer.quit")
    def test_audio_player_start_and_stop(self, mock_quit, mock_stop, mock_play, mock_load, mock_init):
        audio_player = AudioPlayer(audio_file="dummy.wav", delay=0.1, loop=True)
        self.assertFalse(audio_player.is_playing.is_set())
        audio_player.start()
        # Wait a short while to ensure the dummy_play_audio thread is running.
        time.sleep(0.2)
        self.assertTrue(audio_player.is_playing.is_set())
        audio_player.stop()
        self.assertFalse(audio_player.is_playing.is_set())

class TestBenchmarkManager(unittest.TestCase):
    """Tests for the BenchmarkManager."""
    def test_add_benchmark(self):
        stop_event = MagicMock()
        bm = BenchmarkManager(stop_event)
        initial_len = len(bm.benchmarks)
        bm.add_benchmark(
            name="TestBenchmark",
            run_function=dummy_run_function,
            resolution=(800, 600),
            msaa_level=4,
            anisotropy=16,
            shading_model="pbr",
            shadow_map_resolution=2048,
            particle_render_mode="vertex",
            vsync_enabled=True,
            sound_enabled=True,
            fullscreen=False
        )
        self.assertEqual(len(bm.benchmarks), initial_len + 1)

    def test_calculate_performance_score(self):
        bm = BenchmarkManager(MagicMock())
        bm.stats_collector.benchmark_data = {
            "TestBenchmark": {
                "fps_data": [30, 60, 90],
                "cpu_usage_data": [10, 20, 30],
                "gpu_usage_data": [20, 30, 40],
                "elapsed_time": 10
            }
        }
        score = bm.calculate_performance_score()
        expected_avg_fps = (30 + 60 + 90) / 3
        expected_score = int(round(expected_avg_fps * 10))
        self.assertEqual(score, expected_score)

class TestCameraController(unittest.TestCase):
    """Tests for the CameraController class."""
    def test_interpolation(self):
        positions = [
            (0, 0, 0, 0, 0),
            (10, 10, 10, 90, 45)
        ]
        lens_rotations = [0, 90]
        controller = CameraController(positions, lens_rotations=lens_rotations, move_speed=1.0, loop=False)
        pos, rot = controller.update(0.5)
        self.assertAlmostEqual(pos.x, 5, delta=1)
        self.assertAlmostEqual(pos.y, 5, delta=1)
        self.assertAlmostEqual(pos.z, 5, delta=1)
        self.assertAlmostEqual(rot.x, 45, delta=5)
        self.assertAlmostEqual(rot.y, 22.5, delta=5)
        current_lens = controller.get_current_lens_rotation()
        self.assertAlmostEqual(current_lens, 45, delta=10)

class TestSceneConstructor(unittest.TestCase):
    """Tests for the SceneConstructor."""

    def test_add_and_transform_renderer(self):
        sc = SceneConstructor()
        dummy = DummyRenderer("dummy")
        sc.add_renderer("dummy", dummy)
        self.assertIn("dummy", sc.renderers)
        sc.translate_renderer("dummy", (1, 2, 3))
        import glm
        self.assertEqual(dummy.translation, glm.vec3(1, 2, 3))

class TestShaderEngine(unittest.TestCase):
    """Tests for the ShaderEngine class."""
    def setUp(self):
        # Patch discover_shaders for RendererConfig if needed.
        patcher = patch.object(RendererConfig, "discover_shaders", lambda self: None)
        self.addCleanup(patcher.stop)
        patcher.start()

        self.temp_dir = tempfile.mkdtemp()
        self.vertex_shader_path = os.path.join(self.temp_dir, "vertex.glsl")
        self.fragment_shader_path = os.path.join(self.temp_dir, "fragment.glsl")
        with open(self.vertex_shader_path, "w") as f:
            f.write("void main() { gl_Position = vec4(0.0); }")
        with open(self.fragment_shader_path, "w") as f:
            f.write("void main() { }")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    @patch("OpenGL.GL.glCreateShader", return_value=1)
    @patch("OpenGL.GL.glShaderSource")
    @patch("OpenGL.GL.glCompileShader")
    @patch("OpenGL.GL.glGetShaderiv", return_value=True)
    @patch("OpenGL.GL.glGetShaderInfoLog", return_value=b"")
    @patch("OpenGL.GL.glCreateProgram", return_value=1)
    @patch("OpenGL.GL.glAttachShader")
    @patch("OpenGL.GL.glLinkProgram")
    @patch("OpenGL.GL.glGetProgramiv", return_value=True)
    @patch("OpenGL.GL.glDeleteShader")
    @patch("OpenGL.GL.glDeleteProgram")
    def test_shader_engine_creation(self, mock_delProgram, mock_delShader, mock_GetProgramiv,
                                    mock_LinkProgram, mock_AttachShader, mock_CreateProgram,
                                    mock_GetShaderInfoLog, mock_GetShaderiv, mock_CompileShader,
                                    mock_ShaderSource, mock_CreateShader):
        engine = ShaderEngine(vertex_shader_path=self.vertex_shader_path,
                              fragment_shader_path=self.fragment_shader_path)
        self.assertIsNotNone(engine.shader_program)

    def test_shader_engine_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            ShaderEngine(vertex_shader_path="nonexistent.glsl", fragment_shader_path="nonexistent.glsl")

class TestShadowMapManager(unittest.TestCase):
    """Tests for the ShadowMapManager class."""
    @patch("OpenGL.GL.glGenFramebuffers", return_value=1)
    @patch("OpenGL.GL.glGenTextures", return_value=2)
    @patch("OpenGL.GL.glBindTexture")
    @patch("OpenGL.GL.glTexImage2D")
    @patch("OpenGL.GL.glTexParameteri")
    @patch("OpenGL.GL.glFramebufferTexture2D")
    @patch("OpenGL.GL.glDrawBuffer")
    @patch("OpenGL.GL.glReadBuffer")
    @patch("OpenGL.GL.glCheckFramebufferStatus", return_value=0x8CD5)  # GL_FRAMEBUFFER_COMPLETE
    def test_shadow_map_manager_initialization(self, mock_check, mock_read, mock_draw,
                                               mock_fbTexture2D, mock_texParameteri, mock_texImage2D,
                                               mock_bindTexture, mock_genTextures, mock_genFramebuffers):
        smm = ShadowMapManager(shadow_width=1024, shadow_height=1024)
        self.assertEqual(smm.shadow_width, 1024)
        self.assertEqual(smm.shadow_height, 1024)
        import glm
        self.assertTrue(isinstance(smm.light_space_matrix, glm.mat4))

class TestStatsCollector(unittest.TestCase):
    """Tests for the StatsCollector."""
    def test_reset_and_add_data_point(self):
        sc = StatsCollector()
        sc.reset("TestBenchmark", 123)
        self.assertIn("TestBenchmark", sc.benchmark_data)
        sc.set_current_fps(60)
        with sc.usage_lock:
            sc.cpu_usage = 20
            sc.gpu_usage = 30
        sc.add_data_point()
        data = sc.get_all_data()
        self.assertEqual(data["TestBenchmark"]["fps_data"], [60])
        self.assertEqual(data["TestBenchmark"]["cpu_usage_data"], [20])
        self.assertEqual(data["TestBenchmark"]["gpu_usage_data"], [20 + 10])  # Note: test value as set above.
        sc.shutdown()

class TestTextureManager(unittest.TestCase):
    """Tests for the TextureManager singleton."""
    def test_get_texture_unit(self):
        tm = TextureManager()
        unit1 = tm.get_texture_unit("obj1", "diffuse")
        unit2 = tm.get_texture_unit("obj1", "diffuse")
        self.assertEqual(unit1, unit2)
        unit3 = tm.get_texture_unit("obj1", "normal")
        self.assertNotEqual(unit1, unit3)

    @patch("OpenGL.GL.glGenTextures", return_value=10)
    @patch("OpenGL.GL.glBindTexture")
    def test_create_dummy_texture(self, mock_bindTexture, mock_genTextures):
        tm = TextureManager()
        dummy = tm.get_dummy_texture()
        self.assertEqual(dummy, 10)

class TestSurfaceRenderer(unittest.TestCase):
    """Tests for the SurfaceRenderer class."""
    def setUp(self):
        self.renderer = DummySurfaceRenderer(renderer_name="dummy")
        self.renderer.dynamic_attrs = {"width": 10.0, "height": 10.0}

    def test_generate_surface_geometry(self):
        vertices, faces = self.renderer._generate_surface_geometry()
        self.assertIsInstance(vertices, list)
        self.assertIsInstance(faces, list)
        self.assertEqual(len(faces), 2)

class TestSkyboxRenderer(unittest.TestCase):
    """Tests for the SkyboxRenderer class."""
    def setUp(self):
        self.renderer = DummySkyboxRenderer(renderer_name="skybox")

    def test_generate_skybox_vertices(self):
        vertices = self.renderer._generate_skybox_vertices()
        self.assertTrue(len(vertices) >= 36)

class TestRenderInstancing(unittest.TestCase):
    """Tests for the RenderingInstance class."""

    def setUp(self):
        # Patch discover_shaders in RendererConfig so that the config instantiation succeeds.
        patcher = patch.object(RendererConfig, "discover_shaders", lambda self: None)
        self.addCleanup(patcher.stop)
        patcher.start()

    @patch("OpenGL.GL.glGenFramebuffers", return_value=1)
    @patch("OpenGL.GL.glGenTextures", return_value=2)
    def test_add_renderer_and_order(self, mock_genTextures, mock_genFramebuffers):
        config = RendererConfig(window_title="TestInstance", window_size=(800, 600))
        instance = RenderingInstance(config)
        dummy = DummyRenderer("dummy")
        instance.add_renderer("dummy", "model", order=1,
                              obj_path="dummy.obj",
                              texture_paths={"diffuse": "dummy.png"},
                              shader_names=("standard", "default"))
        self.assertIn("dummy", instance.scene_construct.renderers)
        instance.update_render_order("dummy", 0)
        self.assertEqual(instance.render_order[0][1], 0)

# Optionally, test GUI instantiation if available.
try:
    from gui.gui import App
except ImportError:
    App = None

class TestGUI(unittest.TestCase):
    """Basic test to check that the GUI can be instantiated."""
    @unittest.skipUnless(App is not None, "GUI module not available")
    def test_app_instantiation(self):
        app = App()
        self.assertIsNotNone(app)
        app.exit_app()

# --- Main Test Runner --- #

if __name__ == '__main__':
    unittest.main()
