from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.errors import ValidationError  # noqa: E402
from ioitf.cases import load_case_definitions  # noqa: E402
from ioitf.development import load_development_case  # noqa: E402
from ioitf.isa import load_isa_registry  # noqa: E402
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
            path.stem for path in (suite / "cases").glob("*.py")
        }
        self.assertEqual(len(case_names), 176)

        for role, prefix in (("intel", "intel"), ("openpower", "power")):
            sources = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted((suite / role).glob("*.c"))
            )
            self.assertNotIn("example_", sources)
            symbol_pattern = (
                r"[a-z0-9_]+_(?:f32x4|f64x2|[iu]8x16|[iu]16x8|[iu]32x4|[iu]64x2)"
            )
            functions = set(
                re.findall(
                    rf"\b{prefix}_({symbol_pattern})\s*\(",
                    sources,
                )
            )
            shortcuts = set(
                re.findall(
                    rf"\bIOITF_(?:BINARY|UNARY)\([^,]+,[^,]+,\s*{prefix}_({symbol_pattern})\s*,",
                    sources,
                )
            )
            symbols = functions | shortcuts
            operations = {symbol.replace("_", "-") for symbol in symbols}

            with self.subTest(role=role):
                self.assertEqual(operations, case_names)

    def test_official_cases_are_flat_one_file_packs(self) -> None:
        cases = PROJECT / "10_official_suite" / "cases"
        packs = sorted(cases.glob("*.py"))
        self.assertEqual(len(packs), 176)
        self.assertFalse(any(path.is_dir() for path in cases.iterdir()))
        for path in packs:
            source = path.read_text(encoding="utf-8")
            with self.subTest(case=path.stem):
                self.assertLessEqual(
                    len(source.rsplit('"""', 1)[1].splitlines()),
                    8,
                    "move repeated mechanics into ioitf.casepack_families",
                )
                self.assertEqual(source.count('CASE_YAML = """'), 1)
                self.assertIn("from ioitf.casepack_families import ", source)

    def test_new_case_scaffold_creates_a_valid_tiny_model_without_overwriting(self) -> None:
        command = PROJECT / "10_official_suite" / "new-case"
        with tempfile.TemporaryDirectory() as temporary:
            into = Path(temporary) / "cases"
            arguments = [
                sys.executable,
                str(command),
                "demo-add-i32x4",
                "+",
                "--into",
                str(into),
            ]
            created = subprocess.run(arguments, capture_output=True, text=True, check=False)
            self.assertEqual(created.returncode, 0, created.stderr)

            pack = into / "demo-add-i32x4.py"
            source = pack.read_text(encoding="utf-8")
            self.assertEqual([path.name for path in into.iterdir()], [pack.name])
            self.assertIn('CASE_YAML = """', source)
            self.assertLessEqual(len(source.rsplit('"""', 1)[1].splitlines()), 8)

            isa = load_isa_registry(PROJECT / "contracts" / "isa-registry.json")
            cases = load_case_definitions(pack, isa_registry=isa)
            model = load_development_case(cases.get("sse2.demo.add.i32x4.default"))
            self.assertEqual(model.id, "sse2.demo.add.i32x4.default")

            repeated = subprocess.run(arguments, capture_output=True, text=True, check=False)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)
