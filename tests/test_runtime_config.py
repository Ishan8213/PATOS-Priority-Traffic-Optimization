import unittest

from edge.runtime_config import PROJECT_ROOT, display_video_enabled, project_path


class RuntimeConfigTests(unittest.TestCase):
    def test_default_path_is_resolved_from_project_root(self):
        self.assertEqual(
            project_path("PATOS_TEST_PATH", "data/traffic.mp4", {}),
            (PROJECT_ROOT / "data" / "traffic.mp4").resolve(),
        )

    def test_relative_override_is_resolved_from_project_root(self):
        self.assertEqual(
            project_path(
                "PATOS_TEST_PATH",
                "default.json",
                {"PATOS_TEST_PATH": "input/traffic.mp4"},
            ),
            (PROJECT_ROOT / "input" / "traffic.mp4").resolve(),
        )

    def test_absolute_override_is_preserved(self):
        expected = (PROJECT_ROOT / "custom-video.mp4").resolve()
        self.assertEqual(
            project_path(
                "PATOS_TEST_PATH",
                "default.json",
                {"PATOS_TEST_PATH": str(expected)},
            ),
            expected.resolve(),
        )

    def test_display_can_be_disabled_explicitly(self):
        self.assertFalse(display_video_enabled({"PATOS_DISPLAY_VIDEO": "false"}))

    def test_display_can_be_enabled_explicitly(self):
        self.assertTrue(display_video_enabled({"PATOS_DISPLAY_VIDEO": "yes"}))

    def test_invalid_display_setting_is_reported(self):
        with self.assertRaisesRegex(ValueError, "PATOS_DISPLAY_VIDEO"):
            display_video_enabled({"PATOS_DISPLAY_VIDEO": "sometimes"})


if __name__ == "__main__":
    unittest.main()
