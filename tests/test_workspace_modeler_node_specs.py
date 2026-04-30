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

from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.workspace_modeler.workspace_modeler import PackageModeler


def make_package_modeler():
    package_modeler = object.__new__(PackageModeler)
    package_modeler._node_bank = NodeSpecificationBank()
    return package_modeler


def test_update_node_data_uses_package_and_executable_name_as_key():
    package_modeler = make_package_modeler()
    node_names = []

    package_modeler._update_node_data("demo_pkg", node_names, "/tmp/demo_node", None)

    assert node_names == ["demo_node"]
    assert package_modeler.node_specification_bank.keys == ["demo_pkg/demo_node"]

    node_spec = package_modeler.node_specification_bank["demo_pkg/demo_node"]
    assert node_spec.name == "demo_pkg/demo_node"
    assert node_spec.package == "demo_pkg"
    assert node_spec.file_path == "/tmp/demo_node"


def test_update_node_data_merges_multiple_paths_for_same_node():
    package_modeler = make_package_modeler()

    package_modeler._update_node_data(
        "demo_pkg",
        [],
        "/tmp/real/demo_node",
        "/tmp/link/demo_node",
    )
    package_modeler._update_node_data(
        "demo_pkg",
        [],
        "/opt/overlay/demo_node",
        None,
    )

    node_spec = package_modeler.node_specification_bank["demo_pkg/demo_node"]
    assert node_spec.name == "demo_pkg/demo_node"
    assert node_spec.file_path == [
        "/tmp/real/demo_node",
        "/tmp/link/demo_node",
        "/opt/overlay/demo_node",
    ]
