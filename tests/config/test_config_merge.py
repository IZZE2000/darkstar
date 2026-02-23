import shutil
import unittest
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

# Import the target module (will implement the logic here or in config_migration.py)
# For TDD, we define the test first.
# We assume the new function will be exposed in backend.config_migration


class TestConfigMerge(unittest.TestCase):
    def setUp(self):
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.maxDiff = None

    def test_template_fill_merge_structure(self):
        """
        Verify that the merge result strictly follows the DEFAULT structure,
        but contains USER values.
        """
        default_str = """
section_a:
  key1: "default_1"
  key2: "default_2"

section_b:
  key3: "default_3"
"""
        user_str = """
section_b:
  key3: "user_3" # User Changed this

section_a:
  key1: "default_1"
  key2: "user_2" # User Changed this
"""
        # Logic to be implemented:
        # result = merge(default, user)
        # Expected:
        # section_a:
        #   key1: default_1
        #   key2: user_2
        # section_b:
        #   key3: user_3

        default_cfg = self.yaml.load(default_str)
        user_cfg = self.yaml.load(user_str)

        # Placeholder for the actual function call
        # We will implement this logic in the actual file, but for now mimicking the logic
        # to ensure the test case is valid.
        from backend.config_migration import template_aware_merge

        template_aware_merge(default_cfg, user_cfg)

        out = StringIO()
        self.yaml.dump(default_cfg, out)
        result_str = out.getvalue()

        self.assertIn('key2: "user_2"', result_str)
        self.assertIn('key3: "user_3"', result_str)

        # Check Order: section_a MUST come before section_b (as in Default)
        idx_a = result_str.find("section_a")
        idx_b = result_str.find("section_b")
        self.assertLess(idx_a, idx_b, "Section A should come before Section B (Default Order)")

    def test_comment_preservation(self):
        """
        Verify that OFFICIAL comments from Default are preserved.
        """
        default_str = """
# Official Header
section_main:
  # Official Inline
  val: 1
"""
        user_str = """
# User Garbage Comment
section_main:
  val: 99
"""
        default_cfg = self.yaml.load(default_str)
        user_cfg = self.yaml.load(user_str)

        from backend.config_migration import template_aware_merge

        template_aware_merge(default_cfg, user_cfg)

        out = StringIO()
        self.yaml.dump(default_cfg, out)
        result_str = out.getvalue()

        self.assertIn("# Official Header", result_str)
        self.assertIn("# Official Inline", result_str)
        self.assertIn("val: 99", result_str)
        self.assertNotIn("User Garbage Comment", result_str)

    def test_custom_key_preservation(self):
        """
        Verify that keys present in User but NOT in Default are preserved (appended).
        """
        default_str = "core: 1\n"
        user_str = "core: 1\ncustom_plugin: 99\n"

        default_cfg = self.yaml.load(default_str)
        user_cfg = self.yaml.load(user_str)

        from backend.config_migration import template_aware_merge

        template_aware_merge(default_cfg, user_cfg)

        self.assertIn("custom_plugin", default_cfg)
        self.assertEqual(default_cfg["custom_plugin"], 99)

    def test_full_file_integration(self):
        """
        Verify the full migrate_config function with actual files.
        """
        import asyncio

        from backend.config_migration import migrate_config

        # Create temp environment
        test_dir = Path("tests/temp_migration_test")
        test_dir.mkdir(exist_ok=True)

        try:
            # 1. Setup Files
            user_path = test_dir / "config.yaml"
            default_path = test_dir / "config.default.yaml"

            with default_path.open("w") as f:
                f.write("section_a: 1\nsection_b: 2\n")

            with user_path.open("w") as f:
                # User has messed up order and custom value
                f.write("section_b: 99\nsection_a: 1\ncustom: 3\n")

            # 2. Run Migration with lenient validation (for testing minimal configs)
            asyncio.run(migrate_config(str(user_path), str(default_path), strict_validation=False))

            # 3. Verify Result
            with user_path.open() as f:
                content = f.read()

            # Expected: Order A, then B. Value for B is 99. Custom is present.
            idx_a = content.find("section_a")
            idx_b = content.find("section_b")

            self.assertLess(idx_a, idx_b, "File should be reordered (A before B)")
            self.assertIn("section_b: 99", content, "User value 99 should be preserved")
            self.assertIn("custom: 3", content, "Custom key should be preserved")

        finally:
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    unittest.main()
