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

import socket
from types import SimpleNamespace

import pytest

from pydantic import BaseModel

from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.snapshot import snapshot as snapshot_module
from ros2_snapshot.snapshot.ros_model_builder import ROSModelBuilder
from ros2_snapshot.snapshot.snapshot import ROSSnapshot
from ros2_snapshot.snapshot.snapshot import SnapshotProcessingError


def patch_process_lookup(monkeypatch):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_builder.list_ros_like_processes",
        lambda: [],
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_builder.NodeBuilder.get_node_pid",
        lambda self, namespace, node_name, guess=False: None,
    )


def make_strategy():
    class FakeNodeStrategy:
        def __init__(self, *_args, **_kwargs):
            self.direct_node = SimpleNamespace(get_name=lambda: "snapshot_direct")
            self.daemon_node = SimpleNamespace(get_name=lambda: "snapshot_daemon")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    return FakeNodeStrategy


def test_snapshot_returns_false_when_collect_system_info_raises_socket_error(
    monkeypatch,
):
    monkeypatch.setattr(snapshot_module, "NodeStrategy", make_strategy())
    monkeypatch.setattr(
        snapshot_module.ROSSnapshot,
        "collect_system_info",
        lambda self, node, include_hidden_topics=True: (_ for _ in ()).throw(
            socket.error("network down")
        ),
    )

    assert snapshot_module.ROSSnapshot().snapshot() is False


def test_snapshot_returns_false_when_collect_system_info_raises_validation_error(
    monkeypatch,
):
    class DummyModel(BaseModel):
        value: int

    monkeypatch.setattr(snapshot_module, "NodeStrategy", make_strategy())
    monkeypatch.setattr(
        snapshot_module.ROSSnapshot,
        "collect_system_info",
        lambda self, node, include_hidden_topics=True: DummyModel(value="bad"),
    )

    assert snapshot_module.ROSSnapshot().snapshot() is False


def test_call_parameter_service_with_timeout_returns_none_when_services_not_ready(
    monkeypatch,
):
    snapshot = snapshot_module.ROSSnapshot()

    class FakeClient:
        def wait_for_services(self, timeout_sec):
            assert timeout_sec == 1.25
            return False

    monkeypatch.setattr(
        snapshot_module,
        "AsyncParameterClient",
        lambda node, node_name: FakeClient(),
    )

    result = snapshot._call_parameter_service_with_timeout(
        node=object(),
        node_name="/demo_node",
        request_factory=lambda client: None,
        action_description="list parameters",
        timeout=1.25,
    )

    assert result is None


def test_call_parameter_service_with_timeout_returns_none_when_future_result_missing(
    monkeypatch,
):
    snapshot = snapshot_module.ROSSnapshot()
    spin_calls = []

    class FakeFuture:
        def done(self):
            return True

        def result(self):
            return None

        def exception(self):
            return RuntimeError("boom")

    class FakeClient:
        def wait_for_services(self, timeout_sec):
            return True

    future = FakeFuture()
    monkeypatch.setattr(
        snapshot_module,
        "AsyncParameterClient",
        lambda node, node_name: FakeClient(),
    )
    monkeypatch.setattr(
        snapshot_module.rclpy,
        "spin_until_future_complete",
        lambda node, pending_future, timeout_sec=None: spin_calls.append(timeout_sec),
    )

    result = snapshot._call_parameter_service_with_timeout(
        node=object(),
        node_name="/demo_node",
        request_factory=lambda client: future,
        action_description="get parameters",
        timeout=0.75,
    )

    assert result is None
    assert spin_calls == [0.75]


def test_call_parameter_service_with_timeout_returns_response_when_future_completes(
    monkeypatch,
):
    snapshot = snapshot_module.ROSSnapshot()
    spin_calls = []
    response = object()

    class FakeFuture:
        def done(self):
            return True

        def result(self):
            return response

        def exception(self):
            return None

    class FakeClient:
        def wait_for_services(self, timeout_sec):
            assert timeout_sec == 0.5
            return True

    future = FakeFuture()
    monkeypatch.setattr(
        snapshot_module,
        "AsyncParameterClient",
        lambda node, node_name: FakeClient(),
    )
    monkeypatch.setattr(
        snapshot_module.rclpy,
        "spin_until_future_complete",
        lambda node, pending_future, timeout_sec=None: spin_calls.append(
            (node, pending_future, timeout_sec)
        ),
    )

    result = snapshot._call_parameter_service_with_timeout(
        node=object(),
        node_name="/demo_node",
        request_factory=lambda client: future,
        action_description="describe parameters",
        timeout=0.5,
    )

    assert result is response
    assert spin_calls[0][1] is future
    assert spin_calls[0][2] == 0.5


def test_collect_parameters_info_falls_back_to_single_parameter_requests(monkeypatch):
    snapshot = snapshot_module.ROSSnapshot()
    snapshot._ros_model_builder = ROSModelBuilder([])
    get_calls = []

    monkeypatch.setattr(
        snapshot_module,
        "get_node_names",
        lambda **kwargs: [SimpleNamespace(full_name="/demo_node")],
    )
    monkeypatch.setattr(
        snapshot,
        "_list_parameters_with_timeout",
        lambda node, node_name, timeout=2.0: SimpleNamespace(
            result=SimpleNamespace(names=["alpha", "beta"])
        ),
    )

    def fake_get_parameters(node, node_name, parameter_names, timeout=2.0):
        get_calls.append(tuple(parameter_names))
        if len(parameter_names) > 1:
            return SimpleNamespace(values=[])
        if parameter_names == ["alpha"]:
            return SimpleNamespace(values=[11])
        return SimpleNamespace(values=[22])

    monkeypatch.setattr(snapshot, "_get_parameters_with_timeout", fake_get_parameters)
    monkeypatch.setattr(
        snapshot,
        "_describe_parameters_with_timeout",
        lambda node, node_name, parameter_names, timeout=2.0: SimpleNamespace(
            descriptors=[
                SimpleNamespace(name=name, description=f"description:{name}")
                for name in parameter_names
            ]
        ),
    )
    monkeypatch.setattr(
        snapshot_module, "get_value", lambda parameter_value: parameter_value
    )

    snapshot._collect_parameters_info(node=object())

    assert get_calls == [("alpha", "beta"), ("alpha",), ("beta",)]
    assert snapshot.parameter_bank["/demo_node/alpha"].value == 11
    assert snapshot.parameter_bank["/demo_node/beta"].value == 22
    assert (
        snapshot.parameter_bank["/demo_node/alpha"].description == "description:alpha"
    )
    assert snapshot.parameter_bank["/demo_node/beta"].description == "description:beta"


def test_collect_component_info_marks_component_managers_and_components(monkeypatch):
    patch_process_lookup(monkeypatch)

    snapshot = snapshot_module.ROSSnapshot()
    snapshot._ros_model_builder = ROSModelBuilder([])

    monkeypatch.setattr(
        snapshot_module,
        "get_node_names",
        lambda node: [SimpleNamespace(full_name="/container")],
    )
    monkeypatch.setattr(
        snapshot_module,
        "find_container_node_names",
        lambda node, node_names: [SimpleNamespace(full_name="/container")],
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_components_in_container",
        lambda node, remote_container_node_name: (
            0,
            [
                SimpleNamespace(name="/component_a"),
                SimpleNamespace(name="/component_b"),
            ],
        ),
    )

    snapshot._collect_component_info(node=object())

    manager_builder = snapshot.node_bank["/container"]
    component_a_builder = snapshot.node_bank["/component_a"]
    component_b_builder = snapshot.node_bank["/component_b"]

    assert manager_builder.isComponentManager is True
    assert manager_builder.components_list == ["/component_a", "/component_b"]
    assert component_a_builder.isComponent is True
    assert component_a_builder.manager_name == "/container"
    assert component_b_builder.isComponent is True
    assert component_b_builder.manager_name == "/container"


def test_match_token_types_returns_false_for_malformed_builder_entries():
    result = ROSSnapshot._match_token_types(
        "demo_node",
        {"/bad": None},
        {"/bad": object()},
        {"bad": "demo_msgs/msg/Bad"},
    )

    assert result is False


def test_validate_and_update_models_raises_processing_error_instead_of_exiting(
    monkeypatch,
):
    snapshot = ROSSnapshot()
    node_spec_bank = NodeSpecificationBank()
    node_spec_bank["demo_pkg/demo_node"].update_attributes(
        file_path="/tmp/demo_node",
        validated=True,
        parameters={},
        action_clients={},
        action_servers={},
        published_topics={},
        subscribed_topics={},
        services_provided={},
    )
    snapshot._ros_specification_model = ROSModel(
        {BankType.NODE_SPECIFICATION: node_spec_bank}
    )

    node_builder = SimpleNamespace(
        executable_file="/tmp/demo_node",
        executable_cmdline="demo_node",
        executable_name="demo_node",
        set_node_name=lambda name: None,
    )
    snapshot._ros_model_builder = SimpleNamespace(
        get_bank_builder=lambda bank_type: SimpleNamespace(
            items=[("/demo_node", node_builder)]
        )
    )

    monkeypatch.setattr(
        snapshot,
        "_validate_node_builder",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(
        SnapshotProcessingError,
        match="Failed to validate node '/demo_node' \\(demo_pkg/demo_node\\)",
    ):
        snapshot._validate_and_update_models()


def test_list_parameters_with_timeout_returns_none_when_future_never_completes(
    monkeypatch,
):
    snapshot = ROSSnapshot()
    spin_timeouts = []

    class FakeFuture:
        def done(self):
            return False

        def result(self):
            return None

        def exception(self):
            return None

    class FakeClient:
        def wait_for_services(self, timeout_sec):
            return True

        def list_parameters(self, prefixes=None):
            assert prefixes is None
            return FakeFuture()

    monkeypatch.setattr(
        "ros2_snapshot.snapshot.snapshot.AsyncParameterClient",
        lambda node, node_name: FakeClient(),
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.snapshot.rclpy.spin_until_future_complete",
        lambda node, future, timeout_sec=None: spin_timeouts.append(timeout_sec),
    )

    result = snapshot._list_parameters_with_timeout(
        node=object(),
        node_name="/demo_node",
        timeout=1.5,
    )

    assert result is None
    assert spin_timeouts == [1.5]


def test_collect_parameters_info_uses_timed_parameter_helpers(monkeypatch):
    snapshot = ROSSnapshot()
    snapshot._ros_model_builder = ROSModelBuilder([])
    list_calls = []
    get_calls = []
    describe_calls = []

    class FakeDescriptor:
        name = "foo"
        description = "demo"

    monkeypatch.setattr(
        "ros2_snapshot.snapshot.snapshot.get_node_names",
        lambda **kwargs: [SimpleNamespace(full_name="/demo_node")],
    )
    monkeypatch.setattr(
        snapshot,
        "_list_parameters_with_timeout",
        lambda node, node_name, timeout=2.0: (
            list_calls.append(node_name),
            SimpleNamespace(result=SimpleNamespace(names=["foo"])),
        )[1],
    )
    monkeypatch.setattr(
        snapshot,
        "_get_parameters_with_timeout",
        lambda node, node_name, parameter_names, timeout=2.0: (
            get_calls.append((node_name, tuple(parameter_names))),
            SimpleNamespace(values=[123]),
        )[1],
    )
    monkeypatch.setattr(
        snapshot,
        "_describe_parameters_with_timeout",
        lambda node, node_name, parameter_names, timeout=2.0: (
            describe_calls.append((node_name, tuple(parameter_names))),
            SimpleNamespace(descriptors=[FakeDescriptor()]),
        )[1],
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.snapshot.get_value",
        lambda parameter_value: parameter_value,
    )

    snapshot._collect_parameters_info(node=object())

    assert list_calls == ["/demo_node"]
    assert get_calls == [("/demo_node", ("foo",))]
    assert describe_calls == [("/demo_node", ("foo",))]
    assert snapshot.node_bank["/demo_node"].parameter_names == ["/demo_node/foo"]
    assert snapshot.parameter_bank["/demo_node/foo"].value == 123
    assert snapshot.parameter_bank["/demo_node/foo"].description == "demo"
