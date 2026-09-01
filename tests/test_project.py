from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.errors import ValidationError  # noqa: E402
from ioitf.project import load_project  # noqa: E402


class ProjectConfigTests(unittest.TestCase):
    def test_relative_paths_are_resolved_from_the_project_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "nested" / "ioitf.toml"
            project.parent.mkdir()
            project.write_text(
                """[ioitf]
schema_version = 1
suite = "../suite"
isa_registry = "contracts/isa.json"
""",
                encoding="utf-8",
            )
            loaded = load_project(project)
            self.assertEqual(loaded.suite, project.parent / "../suite")
            self.assertEqual(
                loaded.isa_registry, project.parent / "contracts/isa.json"
            )

    def test_project_schema_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "ioitf.toml"
            project.write_text(
                """[ioitf]
schema_version = 1
suite = "suite"
isa_registry = "isa.json"
surprise = true
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "unknown surprise"):
                load_project(project)

            project.write_text(
                """[ioitf]
schema_version = 1.0
suite = "suite"
isa_registry = "isa.json"
""",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "must be integer 1"):
                load_project(project)

    def test_repository_project_points_outside_the_framework_package(self) -> None:
        loaded = load_project(PROJECT / "ioitf.toml")
        self.assertEqual(loaded.suite, PROJECT / "examples" / "sse2")
        self.assertEqual(
            loaded.isa_registry, PROJECT / "contracts" / "isa-registry.json"
        )
