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

from typing import ClassVar

import pytest

from ros2_snapshot.core import metamodels
from ros2_snapshot.core.base_metamodel import (
    CustomSerializationWarning,
    _BankMetamodel,
    _EntityMetamodel,
)
from ros2_snapshot.core.deployments.action import Action
from ros2_snapshot.core.deployments.node import Node
from ros2_snapshot.core.deployments.service import ServiceBank
from ros2_snapshot.core.specifications.node_specification import NodeSpecification
from ros2_snapshot.core.specifications.package_specification import PackageSpecification


def test_update_attributes_promotes_repeated_strings_to_lists():
    node_spec = NodeSpecification(name="demo_pkg/demo_node", file_path="/tmp/one")

    node_spec.update_attributes(file_path="/tmp/two")

    assert node_spec.file_path == ["/tmp/one", "/tmp/two"]


def test_update_attributes_merges_lists_dicts_and_sets():
    package_spec = PackageSpecification(name="demo_pkg", nodes=["node_a"])
    package_spec.update_attributes(nodes=["node_b"])

    node_spec = NodeSpecification(
        name="demo_pkg/demo_node",
        parameters={"alpha": "int"},
    )
    node_spec.update_attributes(parameters={"beta": "str"})

    action = Action(name="/demo_action", client_node_names={"/client_a"})
    action.update_attributes(client_node_names={"/client_b"})

    assert package_spec.nodes == ["node_a", "node_b"]
    assert node_spec.parameters == {"alpha": "int", "beta": "str"}
    assert action.client_node_names == {"/client_a", "/client_b"}


def test_update_attributes_promotes_string_to_set_for_set_typed_fields():
    # Action.client_node_names is Union[Set[str], List[str], str]; str→set should deduplicate.
    action = Action(name="/demo_action", client_node_names="/client_a")

    action.update_attributes(client_node_names="/client_a")  # duplicate
    action.update_attributes(client_node_names="/client_b")

    assert isinstance(action.client_node_names, set)
    assert action.client_node_names == {"/client_a", "/client_b"}


def test_update_attributes_promotes_string_to_list_for_list_only_fields():
    # NodeSpecification.file_path is Union[str, List[str]] (no Set); should remain a list.
    node_spec = NodeSpecification(name="pkg/node", file_path="/a")

    node_spec.update_attributes(file_path="/a")  # duplicate kept in list
    node_spec.update_attributes(file_path="/b")

    assert isinstance(node_spec.file_path, list)
    assert node_spec.file_path == ["/a", "/b"]


def test_update_attributes_increments_version_numbers():
    node_spec = NodeSpecification(name="demo_pkg/demo_node")

    node_spec.update_attributes(version=0)
    node_spec.update_attributes(version=5)

    assert node_spec.version == 6


def test_entity_validation_raises_clear_errors_for_wrong_types():
    with pytest.warns(CustomSerializationWarning, match="client_node_names"):
        with pytest.raises(ValueError, match="client_node_names"):
            Action(name="/demo_action", client_node_names=123)


def test_bank_getitem_creates_entities_lazily_and_stringifies_contents():
    service_bank = ServiceBank()

    service = service_bank["/demo_service"]
    service.update_attributes(source="test")
    rendered = str(service_bank)

    assert service.name == "/demo_service"
    assert "/demo_service" in service_bank
    assert "Services:" in rendered
    assert "name : /demo_service" in rendered


def test_node_can_be_constructed_with_only_common_metadata():
    node = Node(source="ros_snapshot")

    assert node.source == "ros_snapshot"
    assert node.parameter_names is None


def test_model_class_lookup_caches_refresh_for_late_subclasses():
    assert _EntityMetamodel.get_model_class("!Action") is Action
    assert _EntityMetamodel.get_model_class_from_type("Action") is Action
    assert _BankMetamodel.get_model_class("!ServiceBank") is ServiceBank
    assert _BankMetamodel.get_model_class_from_type("ServiceBank") is ServiceBank

    class LateLookupEntity(_EntityMetamodel):
        yaml_tag: ClassVar[str] = "!LateLookupEntity"

    class LateLookupBank(_BankMetamodel):
        yaml_tag: ClassVar[str] = "!LateLookupBank"

    assert _EntityMetamodel.get_model_class("!LateLookupEntity") is LateLookupEntity
    assert (
        _EntityMetamodel.get_model_class_from_type("LateLookupEntity")
        is LateLookupEntity
    )
    assert _BankMetamodel.get_model_class("!LateLookupBank") is LateLookupBank
    assert _BankMetamodel.get_model_class_from_type("LateLookupBank") is LateLookupBank


def test_model_class_lookup_includes_indirect_subclasses():
    assert _EntityMetamodel.get_model_class("!Component") is metamodels.Component
    assert (
        _EntityMetamodel.get_model_class_from_type("Component") is metamodels.Component
    )
