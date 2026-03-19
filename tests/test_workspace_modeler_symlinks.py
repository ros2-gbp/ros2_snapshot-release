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

from pathlib import Path

from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.core.specifications.type_specification import TypeSpecificationBank
from ros2_snapshot.workspace_modeler.workspace_modeler import PackageModeler


def make_package_modeler():
    package_modeler = object.__new__(PackageModeler)
    package_modeler._node_bank = NodeSpecificationBank()
    package_modeler._package_bank = PackageSpecificationBank()
    package_modeler._action_bank = TypeSpecificationBank()
    package_modeler._message_bank = TypeSpecificationBank()
    package_modeler._service_bank = TypeSpecificationBank()
    return package_modeler


def test_find_executable_files_resolves_relative_symlink_targets(tmp_path):
    package_modeler = make_package_modeler()
    executable_dir = tmp_path / "pkg" / "lib" / "demo_pkg" / "nested"
    executable_dir.mkdir(parents=True)
    executable_path = executable_dir / "demo_node"
    executable_path.write_text("#!/bin/sh\n", encoding="utf-8")
    executable_path.chmod(0o755)

    symlink_path = executable_dir.parent / "demo_link"
    symlink_path.symlink_to(Path("nested") / "demo_node")

    node_names = package_modeler._find_executable_files(
        "demo_link",
        str(symlink_path),
        "demo_pkg",
    )

    assert node_names == ["demo_node"]
    node_spec = package_modeler.node_specification_bank["demo_pkg/demo_node"]
    assert node_spec.file_path == [str(executable_path), str(symlink_path)]


def test_collect_package_specs_tracks_paths_inside_relative_symlink_dirs(tmp_path):
    package_modeler = make_package_modeler()
    share_path = tmp_path / "pkg" / "share" / "demo_pkg"
    real_scripts_dir = share_path / "real_scripts"
    real_scripts_dir.mkdir(parents=True)
    executable_path = real_scripts_dir / "demo_node"
    executable_path.write_text("#!/bin/sh\n", encoding="utf-8")
    executable_path.chmod(0o755)

    scripts_symlink = share_path / "scripts"
    scripts_symlink.symlink_to(Path("real_scripts"))

    package_spec = package_modeler.package_specification_bank["demo_pkg"]
    package_modeler._collect_package_specs("demo_pkg", str(share_path), package_spec)

    assert package_spec.nodes == ["demo_node"]

    node_spec = package_modeler.node_specification_bank["demo_pkg/demo_node"]
    assert node_spec.file_path == [
        str(executable_path),
        str(scripts_symlink / "demo_node"),
    ]


def test_find_executable_files_avoids_symlink_cycles(tmp_path):
    package_modeler = make_package_modeler()
    executable_dir = tmp_path / "pkg" / "lib" / "demo_pkg"
    executable_dir.mkdir(parents=True)
    (executable_dir / "loop").symlink_to(Path("."))

    node_names = package_modeler._find_executable_files(
        "loop",
        str(executable_dir / "loop"),
        "demo_pkg",
    )

    assert node_names == []


def test_collect_package_specs_avoids_symlink_cycles(tmp_path):
    package_modeler = make_package_modeler()
    share_path = tmp_path / "pkg" / "share" / "demo_pkg"
    scripts_dir = share_path / "scripts"
    scripts_dir.mkdir(parents=True)
    executable_path = scripts_dir / "demo_node"
    executable_path.write_text("#!/bin/sh\n", encoding="utf-8")
    executable_path.chmod(0o755)
    (share_path / "loop").symlink_to(Path("."))

    package_spec = package_modeler.package_specification_bank["demo_pkg"]
    package_modeler._collect_package_specs("demo_pkg", str(share_path), package_spec)

    assert package_spec.nodes == ["demo_node"]
    assert package_modeler.node_specification_bank["demo_pkg/demo_node"].file_path == (
        str(executable_path)
    )
