from __future__ import annotations

from pathlib import Path
import re
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
        self.assertEqual(loaded.suite, PROJECT / "10_official_suite" / "cases")
        self.assertEqual(
            loaded.isa_registry, PROJECT / "contracts" / "isa-registry.json"
        )

    def test_official_sources_cover_every_case(self) -> None:
        suite = PROJECT / "10_official_suite"
        case_names = {
            path.name
            for path in (suite / "cases").iterdir()
            if (path / "case.yaml").is_file()
        }
        self.assertEqual(len(case_names), 48)

        for role, prefix in (("intel", "intel"), ("openpower", "power")):
            sources = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted((suite / role).glob("*.c"))
            )
            self.assertNotIn("example_", sources)
            symbols = set(
                re.findall(
                    rf"\b{prefix}_([a-z0-9_]+_(?:f64x2|[iu]8x16|[iu]16x8|i32x4))\s*\(",
                    sources,
                )
            )
            operations = {symbol.replace("_", "-") for symbol in symbols}

            with self.subTest(role=role):
                self.assertEqual(operations, case_names)
