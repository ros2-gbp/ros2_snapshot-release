import ast
from pathlib import Path
import re
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _package_xml_version() -> str:
    package_xml = REPO_ROOT / "package.xml"
    version = ET.parse(package_xml).getroot().findtext("version")
    assert version is not None
    return version.strip()


def _setup_py_version() -> str:
    setup_py = REPO_ROOT / "setup.py"
    module = ast.parse(setup_py.read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg == "version":
                assert isinstance(keyword.value, ast.Constant)
                assert isinstance(keyword.value.value, str)
                return keyword.value.value
    raise AssertionError("setup.py must define setup(..., version=\"x.y.z\", ...)")


def test_release_versions_are_consistent():
    package_xml_version = _package_xml_version()
    setup_py_version = _setup_py_version()
    version_file_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert VERSION_RE.match(package_xml_version)
    assert setup_py_version == package_xml_version
    assert version_file_version == package_xml_version
