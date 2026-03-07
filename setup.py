# Copyright 2026 Christopher Newport University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Setup for ros2_snapshot tool."""

import os
from pathlib import Path
import xml.etree.ElementTree as ET

from setuptools import find_packages, setup


def version_from_package_xml(package_xml: Path) -> str:
    tree = ET.parse(package_xml)
    root = tree.getroot()
    ver = root.findtext("version")
    if not ver:
        raise RuntimeError(f"No <version> tag found in {package_xml}")
    return ver.strip()


def write_version_file(version: str, out_path: Path) -> None:
    # Only rewrite if content changed (avoids dirtying git / timestamps unnecessarily)
    content = version + "\n"
    if out_path.exists() and out_path.read_text(encoding="utf-8") == content:
        return
    out_path.write_text(content, encoding="utf-8")


HERE = Path(__file__).resolve().parent
PACKAGE_NAME = "ros2_snapshot"
VERSION = version_from_package_xml(HERE / "package.xml")

write_version_file(VERSION, HERE / "VERSION")

setup(
    name=PACKAGE_NAME,
    version='0.0.2',
    packages=find_packages(),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/ros2_snapshot"],
        ),
        (os.path.join("share", PACKAGE_NAME), ["package.xml"]),
        ("share/" + PACKAGE_NAME, ["VERSION"]),
    ],
    install_requires=[
        "setuptools",
        "graphviz",
        "pydantic",
    ],
    zip_safe=True,
    author="CNU Robotics CHRISLab",
    author_email="robotics@cnu.edu",
    maintainer="CNU Robotics CHRISLab",
    maintainer_email="robotics@cnu.edu",
    keywords=["modeling", "snapshot", "documentation"],
    classifiers=[
        "Intended Audience :: Developers",
        "License :: Apache 2.0",
        "Programming Language :: Python",
        "Topic :: Software Development, Model Driven Engineering (MDE)",
    ],
    description="ros2_snapshot - combines workspace modeling and snapshot functionalities.",
    license="Apache 2.0",
    entry_points={
        "console_scripts": [
            "running = snapshot.snapshot:main",
            "workspace = workspace_modeler.workspace_modeler:main",
        ],
    },
    tests_require=["pytest"],
)
