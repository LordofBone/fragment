"""
test_suite.py

Pytest-compatible tests for the Fragment 3D Rendering Benchmark system.

Covers:
  - RendererConfig
  - AudioPlayer
  - BenchmarkManager
  - CameraController
  - SceneConstructor
  - ShaderEngine  (heavier GL tests are skipped or patched)
  - ShadowMapManager (heavier GL tests are skipped or patched)
  - StatsCollector
  - TextureManager (partially patched)
  - SurfaceRenderer (heavier GL tests are skipped or patched)
  - SkyboxRenderer (heavier GL tests are skipped or patched)
  - RenderingInstance (heavier GL tests are skipped or patched)
  - GUI (basic instantiation tests using a real Pillow image)
  - Additional: enumerates the /shaders folder to test that all shaders compile (skipped if no real context)
  - "Pure Python" logic tests (no OpenGL context needed)
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# Adjust the Python path so that modules from your project can be imported.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ------------------------------------------------------------------------------------
# Import your modules
# ------------------------------------------------------------------------------------
from components.renderer_config import RendererConfig
from components.audio_player import AudioPlayer
from components.benchmark_manager import BenchmarkManager
from components.camera_control import CameraController
from components.scene_constructor import SceneConstructor
from components.shader_engine import ShaderEngine
from components.stats_collector import StatsCollector
from components.surface_renderer import SurfaceRenderer
from components.skybox_renderer import SkyboxRenderer
from components.abstract_renderer import AbstractRenderer


# Instead of a module-level import for App, we define a helper function:
def get_App():
    try:
        from gui.main_gui import App
        return App
    except ImportError:
        return None

# ------------------------------------------------------------------------------------
# Dummy classes and functions for testing
# ------------------------------------------------------------------------------------
def dummy_run_function(stats_queue, stop_event, resolution, msaa_level, anisotropy, shading_model,
                       shadow_map_resolution, particle_render_mode, vsync_enabled, sound_enabled, fullscreen):
    """Fake run function that simulates a short wait and sends 'fps' into stats_queue."""
    if stats_queue is not None:
        stats_queue.put(("ready", None))
        stats_queue.put(("fps", 60))
    time.sleep(0.1)

def dummy_play_audio(self):
    """Fake play_audio function for AudioPlayer, simulating a short wait."""
    self.is_playing.set()
    self.stop_event.wait(timeout=1)
    self.is_playing.clear()

class DummyRenderer(AbstractRenderer):
    """
    A simple concrete subclass of AbstractRenderer for testing.
    It records when create_buffers() and render() are called.
    """
    def __init__(self, renderer_name):
        # We call the parent __init__ normally in tests that do need attributes.
        super().__init__(renderer_name=renderer_name, shader_names={"vertex": "dummy", "fragment": "dummy"})
        self.buffers_created = False
        self.render_called = False
    def create_buffers(self):
        self.buffers_created = True
    def render(self):
        self.render_called = True

class DummySurfaceRenderer(SurfaceRenderer):
    def __init__(self, renderer_name, **kwargs):
        super().__init__(renderer_name=renderer_name,
                         shader_names={"vertex": "dummy", "fragment": "dummy"},
                         **kwargs)
    def create_buffers(self):
        pass
    def render(self):
        pass

class DummySkyboxRenderer(SkyboxRenderer):
    def __init__(self, renderer_name, **kwargs):
        super().__init__(renderer_name=renderer_name,
                         shader_names={"vertex": "dummy", "fragment": "dummy"},
                         **kwargs)
    def create_buffers(self):
        self.vertices = [0.0] * 36
    def render(self):
        pass

# ------------------------------------------------------------------------------------
# Patching OpenGL calls in the OpenGL.GL namespace only.
# ------------------------------------------------------------------------------------
patch_gl_create_shader = patch("OpenGL.GL.glCreateShader", MagicMock(return_value=1))
patch_gl_shader_source = patch("OpenGL.GL.glShaderSource", MagicMock())
patch_gl_compile_shader = patch("OpenGL.GL.glCompileShader", MagicMock())
patch_gl_get_shaderiv = patch("OpenGL.GL.glGetShaderiv", MagicMock(return_value=True))
patch_gl_get_shader_info_log = patch("OpenGL.GL.glGetShaderInfoLog", MagicMock(return_value=b""))
patch_gl_create_program = patch("OpenGL.GL.glCreateProgram", MagicMock(return_value=2))
patch_gl_attach_shader = patch("OpenGL.GL.glAttachShader", MagicMock())
patch_gl_link_program = patch("OpenGL.GL.glLinkProgram", MagicMock())
patch_gl_get_programiv = patch("OpenGL.GL.glGetProgramiv", MagicMock(return_value=True))
patch_gl_delete_shader = patch("OpenGL.GL.glDeleteShader", MagicMock())
patch_gl_delete_program = patch("OpenGL.GL.glDeleteProgram", MagicMock())
patch_gl_gen_framebuffers = patch("OpenGL.GL.glGenFramebuffers", MagicMock(return_value=3))
patch_gl_gen_textures = patch("OpenGL.GL.glGenTextures", MagicMock(return_value=4))
patch_gl_bind_texture = patch("OpenGL.GL.glBindTexture", MagicMock())
patch_gl_tex_image2d = patch("OpenGL.GL.glTexImage2D", MagicMock())
patch_gl_tex_parameteri = patch("OpenGL.GL.glTexParameteri", MagicMock())
patch_gl_framebuffer_texture2d = patch("OpenGL.GL.glFramebufferTexture2D", MagicMock())
patch_gl_draw_buffer = patch("OpenGL.GL.glDrawBuffer", MagicMock())
patch_gl_read_buffer = patch("OpenGL.GL.glReadBuffer", MagicMock())
patch_gl_check_framebuffer = patch("OpenGL.GL.glCheckFramebufferStatus", MagicMock(return_value=0x8CD5))
patch_gl_delete_framebuffers = patch("OpenGL.GL.glDeleteFramebuffers", MagicMock())
patch_gl_delete_textures = patch("OpenGL.GL.glDeleteTextures", MagicMock())

def patched_gl(cls):
    """Class decorator applying all needed OpenGL patches."""
    patches = [
        patch_gl_create_shader,
        patch_gl_shader_source,
        patch_gl_compile_shader,
        patch_gl_get_shaderiv,
        patch_gl_get_shader_info_log,
        patch_gl_create_program,
        patch_gl_attach_shader,
        patch_gl_link_program,
        patch_gl_get_programiv,
        patch_gl_delete_shader,
        patch_gl_delete_program,
        patch_gl_gen_framebuffers,
        patch_gl_gen_textures,
        patch_gl_bind_texture,
        patch_gl_tex_image2d,
        patch_gl_tex_parameteri,
        patch_gl_framebuffer_texture2d,
        patch_gl_draw_buffer,
        patch_gl_read_buffer,
        patch_gl_check_framebuffer,
        patch_gl_delete_framebuffers,
        patch_gl_delete_textures,
    ]
    for p in patches:
        cls = p(cls)
    return cls

# ------------------------------------------------------------------------------------
# PURE PYTHON LOGIC TESTS (no OpenGL context needed)
# ------------------------------------------------------------------------------------
class TestPurePythonLogic(unittest.TestCase):
    def test_camera_controller_no_loop(self):
        positions = [
            (0, 0, 0, 0, 0),
            (10, 10, 10, 90, 45)
        ]
        lens = [0, 90]
        c = CameraController(positions, lens_rotations=lens, move_speed=1.0, loop=False)
        pos, rot = c.update(0.2)
        self.assertGreater(pos.x, 0.0)
        self.assertLess(pos.x, 10.0)

    @patch.object(RendererConfig, 'discover_shaders', lambda self: None)
    def test_renderer_config_without_gl(self):
        base = RendererConfig(window_title="TestNoGL", window_size=(640, 480))
        self.assertEqual(base.window_title, "TestNoGL")
        self.assertEqual(base.window_size, (640, 480))
        surf_cfg = base.add_surface(shader_names=("surface_test_v", "surface_test_f"))
        self.assertEqual(surf_cfg["shader_names"], ("surface_test_v", "surface_test_f"))

    def test_scene_transformations(self):
        sc = SceneConstructor()
        # Patch AbstractRenderer.__init__ to bypass GL initialization.
        with patch.object(AbstractRenderer, '__init__', return_value=None):
            dummy = DummyRenderer("dummy_no_gl")
            # Manually set required transformation defaults.
            import glm
            dummy.translation = glm.vec3(0, 0, 0)
            dummy.rotation = glm.vec3(0, 0, 0)
            dummy.scaling = glm.vec3(1, 1, 1)
        sc.renderers["dummy_no_gl"] = dummy
        # Now apply transformations
        import glm
        sc.translate_renderer("dummy_no_gl", (5, 6, 7))
        self.assertEqual(dummy.translation, glm.vec3(5, 6, 7))
        sc.rotate_renderer_euler("dummy_no_gl", (90, 0, 0))
        self.assertAlmostEqual(dummy.rotation.x, glm.radians(90.0), places=4)
        sc.scale_renderer("dummy_no_gl", (2, 2, 2))
        self.assertEqual(dummy.scaling, glm.vec3(2, 2, 2))


# ------------------------------------------------------------------------------------
# TESTS THAT REQUIRE PARTIAL GL CALLS (skipped for now unless a headless GL context is set up)
# ------------------------------------------------------------------------------------
@unittest.skip("Needs real GL context or heavier patching to avoid NullFunctionError.", )
@patched_gl
class TestShaderEngine(unittest.TestCase):
    def setUp(self):
        pass

    def test_shader_engine_creation(self):
        pass


@unittest.skip("Needs real GL context or heavier patching to avoid NullFunctionError.", )
@patched_gl
class TestShadowMapManager(unittest.TestCase):
    def test_shadow_map_manager_initialization(self):
        pass


@unittest.skip("Needs real GL context or heavier patching to avoid NullFunctionError.", )
@patched_gl
class TestRenderInstancing(unittest.TestCase):
    def test_add_renderer_and_order(self):
        pass


@unittest.skip("Needs real GL context or heavier patching to avoid NullFunctionError.", )
@patched_gl
class TestAllShadersCompilation(unittest.TestCase):
    def setUp(self):
        def discover_shaders_override(self):
            shader_root = os.path.join(PROJECT_ROOT, "shaders")
            if not os.path.exists(shader_root):
                raise FileNotFoundError(f"The shader root directory '{shader_root}' does not exist.")

        RendererConfig.discover_shaders = discover_shaders_override
        self.shaders_root = os.path.join(PROJECT_ROOT, "shaders")

    def test_compile_all_shaders(self):
        def find_shader_files(shader_type):
            base = os.path.join(self.shaders_root, shader_type)
            if not os.path.isdir(base):
                return []
            subfolders = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
            results = []
            for sf in subfolders:
                path = os.path.join(base, sf, f"{shader_type}.glsl")
                if os.path.isfile(path):
                    results.append(path)
            return results

        all_vertex_shaders = find_shader_files("vertex")
        all_fragment_shaders = find_shader_files("fragment")
        all_compute_shaders = find_shader_files("compute")
        for vtx_path in all_vertex_shaders:
            engine = ShaderEngine(vertex_shader_path=vtx_path, fragment_shader_path=None)
            self.assertIsNotNone(engine.shader_program, f"Vertex shader compile failed: {vtx_path}")
        for frag_path in all_fragment_shaders:
            engine = ShaderEngine(vertex_shader_path=None, fragment_shader_path=frag_path)
            self.assertIsNotNone(engine.shader_program, f"Fragment shader compile failed: {frag_path}")
        for cmp_path in all_compute_shaders:
            engine = ShaderEngine(vertex_shader_path=None, fragment_shader_path=None,
                                  compute_shader_path=cmp_path)
            self.assertIsNotNone(engine.compute_shader_program, f"Compute shader compile failed: {cmp_path}")


@unittest.skip("Needs real GL context or heavier patching to avoid NullFunctionError.", )
@patched_gl
class TestSkyboxRenderer(unittest.TestCase):
    def test_generate_skybox_vertices(self):
        pass


@unittest.skip("Needs real GL context or heavier patching to avoid NullFunctionError.", )
@patched_gl
class TestSurfaceRenderer(unittest.TestCase):
    def test_generate_surface_geometry(self):
        pass

# ------------------------------------------------------------------------------------
# Tests that do not require GL calls (or minimal ones)
# ------------------------------------------------------------------------------------
@patched_gl
class TestRendererConfigGL(unittest.TestCase):
    def setUp(self):
        RendererConfig.discover_shaders = lambda s: None
        self.config = RendererConfig(window_title="TestRenderer", window_size=(800, 600))
    def test_add_model_returns_valid_config(self):
        model_config = self.config.add_model(
            obj_path="dummy.obj",
            texture_paths={"diffuse": "dummy.png"},
            shader_names=("standard", "default")
        )
        self.assertIsInstance(model_config, dict)
        self.assertEqual(model_config["obj_path"], "dummy.obj")
    def test_add_surface_returns_valid_config(self):
        surface_config = self.config.add_surface(shader_names=("surface_vertex", "surface_fragment"))
        self.assertEqual(surface_config["shader_names"], ("surface_vertex", "surface_fragment"))
    def test_add_skybox_returns_valid_config(self):
        skybox_config = self.config.add_skybox(
            cubemap_folder="dummy_cube", shader_names=("skybox_vertex", "skybox_fragment")
        )
        self.assertEqual(skybox_config["cubemap_folder"], "dummy_cube")
    def test_add_particle_renderer_returns_valid_config(self):
        particle_config = self.config.add_particle_renderer(
            particle_render_mode="cpu", shader_names=("particle_vertex", "particle_fragment")
        )
        self.assertEqual(particle_config["particle_render_mode"], "cpu")


# ------------------------------------------------------------------------------------
# Tests for modules that do not require a GL context at all
# ------------------------------------------------------------------------------------
class TestAudioPlayer(unittest.TestCase):
    @patch.object(AudioPlayer, "play_audio", new=dummy_play_audio)
    @patch("pygame.mixer.init", MagicMock())
    @patch("pygame.mixer.music.load", MagicMock())
    @patch("pygame.mixer.music.play", MagicMock())
    @patch("pygame.mixer.music.stop", MagicMock())
    @patch("pygame.mixer.quit", MagicMock())
    def test_audio_player_start_and_stop(self):
        audio_player = AudioPlayer(audio_file="dummy.wav", delay=0.1, loop=True)
        self.assertFalse(audio_player.is_playing.is_set())
        audio_player.start()
        time.sleep(0.2)
        self.assertTrue(audio_player.is_playing.is_set())
        audio_player.stop()
        self.assertFalse(audio_player.is_playing.is_set())

class TestBenchmarkManager(unittest.TestCase):
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
        self.assertEqual(score, int(round(((30 + 60 + 90) / 3) * 10)))

class TestCameraController(unittest.TestCase):
    def test_interpolation(self):
        positions = [
            (0, 0, 0, 0, 0),
            (10, 10, 10, 90, 45)
        ]
        lens_rotations = [0, 90]
        controller = CameraController(positions, lens_rotations=lens_rotations, move_speed=1.0, loop=False)
        pos, rot = controller.update(0.5)
        self.assertGreaterEqual(pos.x, 4.5)
        self.assertLessEqual(pos.x, 5.5)
        self.assertGreaterEqual(rot.x, 40)
        self.assertLessEqual(rot.x, 50)

class TestSceneConstructor(unittest.TestCase):
    def test_add_and_transform_renderer(self):
        sc = SceneConstructor()
        # Patch out the AbstractRenderer initializer to avoid GL calls
        with patch.object(AbstractRenderer, '__init__', return_value=None):
            dummy = DummyRenderer("dummy")
            # Manually set default transformation attributes
            import glm
            dummy.translation = glm.vec3(0, 0, 0)
            dummy.rotation = glm.vec3(0, 0, 0)
            dummy.scaling = glm.vec3(1, 1, 1)
            sc.add_renderer("dummy", dummy)
        import glm
        sc.translate_renderer("dummy", (1, 2, 3))
        self.assertEqual(dummy.translation, glm.vec3(1, 2, 3))

class TestStatsCollector(unittest.TestCase):
    def test_reset_and_add_data_point(self):
        sc = StatsCollector()
        sc.reset("TestBenchmark", 123)
        self.assertIn("TestBenchmark", sc.benchmark_data)
        sc.set_current_fps(60)
        with sc.usage_lock:
            sc.cpu_usage = 20.0
            sc.gpu_usage = 30.0
        sc.add_data_point()
        data = sc.get_all_data()
        self.assertEqual(data["TestBenchmark"]["fps_data"], [60])
        self.assertEqual(data["TestBenchmark"]["cpu_usage_data"], [20.0])
        self.assertEqual(data["TestBenchmark"]["gpu_usage_data"], [30.0])
        sc.shutdown()

@patch("PIL.Image.open")
class TestGUI(unittest.TestCase):
    @unittest.skipIf(get_App() is None, "GUI module not available or cannot be imported.")
    def test_app_instantiation(self, mock_image_open):
        """
        Check that the App can be created and destroyed without error,
        using a real Pillow Image. Instead of calling mainloop() (which blocks),
        we run a loop for a short duration and then exit.
        """
        # Create a real Pillow image to use in the GUI (so that paste() works correctly)
        fake_img = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
        mock_image_open.return_value = fake_img

        App = get_App()
        self.assertIsNotNone(App, "Failed to import App from gui.main_gui")
        app = App()
        self.assertIsNotNone(app, "App() returned None")

        # Schedule the app to exit after 200 ms
        app.after(200, app.exit_app)

        # Instead of calling app.mainloop() which blocks indefinitely,
        # we simulate a short main loop by polling for events.
        start_time = time.time()
        while time.time() - start_time < 1:  # run for about 1 second
            app.update()
        # Ensure the app is destroyed so that it does not block further tests.
        app.destroy()
