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

import pytest

from ros2_snapshot.core.deployments.service import Service, ServiceBank
from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.snapshot.snapshot import ROSSnapshot


def test_update_bank_merges_entities_into_existing_bank():
    model = ROSModel({BankType.SERVICE: ServiceBank()})
    service = Service(name="/demo_service")

    model.update_bank(BankType.SERVICE, {"/demo_service": service})

    assert model.service_bank.keys == ["/demo_service"]
    assert model.service_bank["/demo_service"] is service


def test_update_bank_initializes_missing_bank_from_bank_type():
    model = ROSModel({})
    service = Service(name="/demo_service")

    model.update_bank(BankType.SERVICE, {"/demo_service": service})

    assert isinstance(model[BankType.SERVICE], ServiceBank)
    assert model.service_bank.keys == ["/demo_service"]
    assert model.service_bank["/demo_service"] is service


def test_snapshot_package_specification_bank_uses_package_specification_type():
    package_bank = PackageSpecificationBank()
    snapshot = ROSSnapshot()
    snapshot._ros_specification_model = ROSModel(
        {BankType.PACKAGE_SPECIFICATION: package_bank}
    )

    assert snapshot.package_specification_bank is package_bank


def test_node_bank_builder_loads_fresh_processes_on_each_init(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.list_ros_like_processes",
        lambda: calls.append("loaded") or [],
    )

    from ros2_snapshot.snapshot.builders.node_bank_builder import NodeBankBuilder

    NodeBankBuilder()
    NodeBankBuilder()

    assert calls == ["loaded", "loaded"]


def test_node_bank_builder_merges_remote_processes_with_local_processes(monkeypatch):
    ip_lookup_calls = []
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.socket.gethostname",
        lambda: "local_host",
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.get_ip_addresses",
        lambda hostname, preferred_addresses=None: ip_lookup_calls.append(
            (hostname, preferred_addresses)
        )
        or ["192.0.2.30", "127.0.1.1"],
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.get_ros_network_environment",
        lambda: {"ROS_DISCOVERY_SERVER": "192.0.2.30:11811"},
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.get_machine_id",
        lambda: ("local-machine-id", "/etc/machine-id"),
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.list_ros_like_processes",
        lambda: [
            {
                "pid": 10,
                "ppid": 1,
                "name": "local_node",
                "cmdline": ["local_node"],
                "assigned": None,
            }
        ],
    )

    from ros2_snapshot.snapshot.builders.node_bank_builder import NodeBankBuilder

    node_bank_builder = NodeBankBuilder(
        [
            {
                "pid": 10,
                "ppid": 1,
                "name": "remote_node",
                "cmdline": ["remote_node"],
                "assigned": None,
                "machine": "remote_host",
            }
        ]
    )

    assert set(node_bank_builder.processes) == {"remote_host:10", "local_host:10"}
    assert node_bank_builder.processes["remote_host:10"]["name"] == "remote_node"
    assert node_bank_builder.processes["local_host:10"]["name"] == "local_node"
    assert node_bank_builder.processes["local_host:10"]["machine_ip_addresses"] == [
        "192.0.2.30",
        "127.0.1.1",
    ]
    assert node_bank_builder.processes["local_host:10"][
        "machine_ros_network_environment"
    ] == {"ROS_DISCOVERY_SERVER": "192.0.2.30:11811"}
    assert node_bank_builder.processes["local_host:10"][
        "machine_ros_network_address_hints"
    ] == ["192.0.2.30"]
    assert node_bank_builder.processes["local_host:10"]["machine_id"] == (
        "local-machine-id"
    )
    assert ip_lookup_calls == [("local_host", ["192.0.2.30"])]


def test_node_bank_builder_merges_duplicate_machine_id_pid_processes(monkeypatch):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.list_ros_like_processes",
        lambda: [],
    )

    from ros2_snapshot.snapshot.builders.node_bank_builder import NodeBankBuilder

    node_bank_builder = NodeBankBuilder(
        [
            {
                "pid": 10,
                "ppid": 1,
                "name": "talker",
                "cmdline": ["talker"],
                "assigned": None,
                "machine": "robot",
                "machine_id": "same-machine",
            },
            {
                "pid": 10,
                "ppid": 1,
                "name": "talker",
                "cmdline": ["talker"],
                "assigned": None,
                "machine": "robot_local",
                "machine_id": "same-machine",
                "machine_ip_addresses": ["192.0.2.10"],
            },
        ]
    )

    assert set(node_bank_builder.processes) == {"robot:10"}
    assert node_bank_builder.processes["robot:10"]["machine_ip_addresses"] == [
        "192.0.2.10"
    ]


def test_node_bank_builder_keeps_ambiguous_duplicate_process_keys(monkeypatch, caplog):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.list_ros_like_processes",
        lambda: [],
    )

    from ros2_snapshot.snapshot.builders.node_bank_builder import NodeBankBuilder
    from ros2_snapshot.snapshot.builders.node_bank_builder import LoggerLevel

    with caplog.at_level(LoggerLevel.WARNING):
        node_bank_builder = NodeBankBuilder(
            [
                {
                    "pid": 10,
                    "ppid": 1,
                    "name": "first",
                    "cmdline": ["first"],
                    "assigned": None,
                    "machine": "robot",
                    "process_key": "ambiguous:10",
                },
                {
                    "pid": 10,
                    "ppid": 1,
                    "name": "second",
                    "cmdline": ["second"],
                    "assigned": None,
                    "machine": "other_robot",
                    "process_key": "ambiguous:10",
                },
            ]
        )

    assert set(node_bank_builder.processes) == {"ambiguous:10", "ambiguous:10#2"}
    assert node_bank_builder.processes["ambiguous:10"]["name"] == "first"
    assert node_bank_builder.processes["ambiguous:10#2"]["name"] == "second"
    assert "Duplicate process key 'ambiguous:10' detected" in caplog.text


def test_node_bank_builder_marks_unmatched_nodes_unknown_when_remotes_seen(monkeypatch):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.list_ros_like_processes",
        lambda: [],
    )

    from ros2_snapshot.snapshot.builders.node_bank_builder import NodeBankBuilder
    from ros2_snapshot.snapshot.builders.node_builder import UNKNOWN_MACHINE

    node_bank_builder = NodeBankBuilder([])
    node_builder = node_bank_builder["/unmatched"]
    node_builder._process_dict = {}

    assert node_builder.machine == UNKNOWN_MACHINE
