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

from types import SimpleNamespace

from ros2_snapshot.snapshot.snapshot import ROSSnapshot
from ros2_snapshot.core.specifications.node_specification import NodeSpecification
from ros2_snapshot.core.ros_model import BankType


def make_snapshot_with_param_bank(param_bank):
    snapshot = ROSSnapshot()
    snapshot._ros_model_builder = SimpleNamespace(
        get_bank_builder=lambda bank_type: (
            param_bank if bank_type == BankType.PARAMETER else {}
        )
    )
    return snapshot


def make_node_builder(parameter_names):
    return SimpleNamespace(
        parameter_names=parameter_names,
        action_clients=[],
        action_servers=[],
        published_topic_names=[],
        subscribed_topic_names=[],
        service_names_with_remap=[],
    )


def test_update_node_specification_reuses_existing_parameter_entries():
    snapshot = make_snapshot_with_param_bank(
        {"foo": SimpleNamespace(construct_type="int")}
    )
    node_spec = NodeSpecification(name="demo_pkg/demo_node", parameters={"foo": "int"})

    snapshot._update_node_specification(node_spec, make_node_builder(["foo"]))

    assert node_spec.parameters == {"foo": "int"}


def test_update_node_specification_keeps_suffixes_for_real_token_collisions():
    snapshot = make_snapshot_with_param_bank(
        {
            "/ns1/foo": SimpleNamespace(construct_type="int"),
            "/ns2/foo": SimpleNamespace(construct_type="int"),
        }
    )
    node_spec = NodeSpecification(name="demo_pkg/demo_node", parameters={})

    snapshot._update_node_specification(
        node_spec,
        make_node_builder(["/ns1/foo", "/ns2/foo"]),
    )

    assert node_spec.parameters == {"foo": "int", "foo_1": "int"}


def test_update_node_specification_preserves_real_numeric_suffix_tokens():
    snapshot = make_snapshot_with_param_bank(
        {"/ns/camera_1": SimpleNamespace(construct_type="int")}
    )
    node_spec = NodeSpecification(
        name="demo_pkg/demo_node",
        parameters={"camera_1": "int"},
    )

    snapshot._update_node_specification(
        node_spec,
        make_node_builder(["/ns/camera_1"]),
    )

    assert node_spec.parameters == {"camera_1": "int"}


def test_update_node_specification_does_not_reuse_numeric_suffix_tokens_for_other_names():
    snapshot = make_snapshot_with_param_bank(
        {"/ns/camera": SimpleNamespace(construct_type="int")}
    )
    node_spec = NodeSpecification(
        name="demo_pkg/demo_node",
        parameters={"camera_1": "int"},
    )

    snapshot._update_node_specification(
        node_spec,
        make_node_builder(["/ns/camera"]),
    )

    assert node_spec.parameters == {"camera_1": "int", "camera": "int"}


def test_validate_node_builder_checks_parameter_tokens_once(monkeypatch):
    snapshot = ROSSnapshot()
    snapshot._ros_model_builder = SimpleNamespace(get_bank_builder=lambda bank_type: {})
    node_spec = NodeSpecification(
        name="demo_pkg/demo_node",
        parameters={},
        action_clients={},
        action_servers={},
        published_topics={},
        subscribed_topics={},
        services_provided={},
    )
    node_builder = make_node_builder([])

    calls = []

    def fake_match_token_types(node_name, io_names, io_builders, spec_types):
        calls.append((node_name, io_names, spec_types))
        return True

    monkeypatch.setattr(
        ROSSnapshot,
        "_match_token_types",
        staticmethod(fake_match_token_types),
    )

    assert snapshot._validate_node_builder(
        "demo_pkg/demo_node", node_builder, node_spec
    )
    assert len(calls) == 6


def test_validate_node_builder_allows_missing_parameter_spec_section():
    snapshot = ROSSnapshot()
    snapshot._ros_model_builder = SimpleNamespace(get_bank_builder=lambda bank_type: {})
    node_spec = NodeSpecification(
        name="demo_pkg/demo_node",
        validated=True,
        parameters=None,
        action_clients={},
        action_servers={},
        published_topics={},
        subscribed_topics={},
        services_provided={},
    )
    node_builder = make_node_builder([])

    assert snapshot._validate_node_builder(
        "demo_pkg/demo_node",
        node_builder,
        node_spec,
    )
