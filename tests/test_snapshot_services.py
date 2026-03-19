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

from ros2_snapshot.snapshot.builders.service_bank_builder import ServiceBankBuilder
from ros2_snapshot.snapshot import snapshot as snapshot_module
from ros2_snapshot.snapshot.ros_model_builder import ROSModelBuilder


def test_collect_system_info_uses_service_client_api(monkeypatch):
    ros_snapshot = snapshot_module.ROSSnapshot()
    ros_node = SimpleNamespace(full_name="/demo_node")
    service_server = SimpleNamespace(
        name="/demo_server",
        types=["std_srvs/srv/Empty"],
    )
    service_client = SimpleNamespace(
        name="/demo_client",
        types=["example_interfaces/srv/AddTwoInts"],
    )

    monkeypatch.setattr(
        snapshot_module,
        "get_node_names",
        lambda node, include_hidden_nodes=True: [ros_node],
    )
    monkeypatch.setattr(snapshot_module, "get_action_server_info", lambda **kwargs: [])
    monkeypatch.setattr(snapshot_module, "get_action_client_info", lambda **kwargs: [])
    monkeypatch.setattr(snapshot_module, "get_publisher_info", lambda **kwargs: [])
    monkeypatch.setattr(snapshot_module, "get_subscriber_info", lambda **kwargs: [])
    monkeypatch.setattr(
        snapshot_module,
        "get_service_server_info",
        lambda **kwargs: [service_server],
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_service_client_info",
        lambda **kwargs: [service_client],
    )

    _, nodes, services, _ = ros_snapshot.collect_system_info(node=object())

    assert nodes == [ros_node]
    assert services["/demo_server"]["servers"] == {"/demo_node"}
    assert services["/demo_server"]["clients"] == set()
    assert services["/demo_server"]["types"] == {"std_srvs/srv/Empty"}
    assert services["/demo_client"]["servers"] == set()
    assert services["/demo_client"]["clients"] == {"/demo_node"}
    assert services["/demo_client"]["types"] == {"example_interfaces/srv/AddTwoInts"}


def test_collect_services_info_tracks_service_clients_and_providers():
    ros_snapshot = snapshot_module.ROSSnapshot()
    ros_snapshot._ros_model_builder = ROSModelBuilder([])

    ros_snapshot._collect_services_info(
        {
            "/demo_service": {
                "servers": {"/server_node"},
                "clients": {"/client_node"},
                "types": {"std_srvs/srv/Empty"},
            }
        }
    )

    service_builder = ros_snapshot.service_bank["/demo_service"]
    assert service_builder.service_provider_node_names == ["/server_node"]
    assert service_builder.service_client_node_names == ["/client_node"]

    server_node = ros_snapshot.node_bank["/server_node"]
    client_node = ros_snapshot.node_bank["/client_node"]
    assert server_node.service_names_to_types == {"/demo_service": "std_srvs/srv/Empty"}
    assert client_node.service_names_to_types == {}


def test_collect_services_info_marks_ambiguous_service_types_explicitly():
    ros_snapshot = snapshot_module.ROSSnapshot()
    ros_snapshot._ros_model_builder = ROSModelBuilder([])

    ros_snapshot._collect_services_info(
        {
            "/demo_service": {
                "servers": {"/server_node"},
                "clients": set(),
                "types": {"pkg/srv/A", "pkg/srv/B"},
            }
        }
    )

    expected_type = "[multiple] pkg/srv/A | pkg/srv/B"
    service_builder = ros_snapshot.service_bank["/demo_service"]
    server_node = ros_snapshot.node_bank["/server_node"]

    assert service_builder.construct_type == expected_type
    assert server_node.service_names_to_types == {"/demo_service": expected_type}


def test_service_metamodel_preserves_client_node_names():
    ros_snapshot = snapshot_module.ROSSnapshot()
    ros_snapshot._ros_model_builder = ROSModelBuilder([])

    service_builder = ros_snapshot.service_bank["/demo_service"]
    service_builder.add_service_provider_node_name("/server_node")
    service_builder.add_service_client_node_name("/client_node")
    service_builder.construct_type = "std_srvs/srv/Empty"

    service = service_builder.extract_metamodel()

    assert service.service_provider_node_names == ["/server_node"]
    assert service.service_client_node_names == ["/client_node"]


def test_service_bank_prepare_uses_cached_types_without_live_requery(monkeypatch):
    service_bank = ServiceBankBuilder()
    service_builder = service_bank["/demo_service"]
    service_builder.construct_type = "std_srvs/srv/Empty"

    def fail_live_lookup(*_args, **_kwargs):
        raise AssertionError("live service lookup should not run")

    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.service_builder.get_service_names_and_types",
        fail_live_lookup,
        raising=False,
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.service_builder.NodeStrategy",
        fail_live_lookup,
        raising=False,
    )

    service_bank.prepare()
    service = service_builder.extract_metamodel()

    assert service.construct_type == "std_srvs/srv/Empty"
