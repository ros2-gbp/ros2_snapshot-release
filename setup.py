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

from setuptools import find_packages, setup


PACKAGE_NAME = "ros2_snapshot"

setup(
    name=PACKAGE_NAME,
    version="0.0.7",
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
        "pydantic>=1.10.17,<3",
        "psutil",
        "PyYAML",
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
            "remote = ros2_snapshot.snapshot.snapshot_remote:main",
            "running = ros2_snapshot.snapshot.snapshot:main",
            "workspace = ros2_snapshot.workspace_modeler.workspace_modeler:main",
        ],
    },
    tests_require=["pytest"],
)
