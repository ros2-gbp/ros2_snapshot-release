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

from ros2_snapshot.core.deployments.action import Action, ActionBank
from ros2_snapshot.core.deployments.machine import MachineBank
from ros2_snapshot.core.deployments.node import NodeBank
from ros2_snapshot.core.deployments.parameter import ParameterBank
from ros2_snapshot.core.deployments.service import Service, ServiceBank
from ros2_snapshot.core.deployments.topic import TopicBank
from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.core.specifications.type_specification import TypeSpecificationBank
from ros2_snapshot.core.utilities.utility import get_input_file_type


def make_full_model():
    return ROSModel(
        {
            BankType.NODE: NodeBank(),
            BankType.TOPIC: TopicBank(),
            BankType.ACTION: ActionBank(),
            BankType.SERVICE: ServiceBank(),
            BankType.PARAMETER: ParameterBank(),
            BankType.MACHINE: MachineBank(),
            BankType.PACKAGE_SPECIFICATION: PackageSpecificationBank(),
            BankType.NODE_SPECIFICATION: NodeSpecificationBank(),
            BankType.MESSAGE_SPECIFICATION: TypeSpecificationBank(),
            BankType.SERVICE_SPECIFICATION: TypeSpecificationBank(),
            BankType.ACTION_SPECIFICATION: TypeSpecificationBank(),
        }
    )


@pytest.mark.parametrize(
    ("input_type", "reader_name"),
    [
        ("json", "read_model_from_json"),
        ("yaml", "read_model_from_yaml"),
        ("pkl", "read_model_from_pickle"),
    ],
)
def test_load_model_dispatches_to_expected_reader(monkeypatch, input_type, reader_name):
    expected_model = object()

    monkeypatch.setattr(
        "ros2_snapshot.core.ros_model.get_input_file_type",
        lambda directory_path: (input_type, "snapshot"),
    )
    monkeypatch.setattr(
        ROSModel,
        reader_name,
        staticmethod(
            lambda directory_path, base_file_name, spec_only=False: expected_model
        ),
    )

    assert ROSModel.load_model("/tmp/demo", spec_only=True) is expected_model


def test_load_model_returns_none_for_empty_directories(tmp_path):
    assert ROSModel.load_model(tmp_path) is None


def test_get_input_file_type_raises_for_mixed_extensions(tmp_path):
    (tmp_path / "snapshot_node_bank.json").write_text("{}", encoding="utf-8")
    (tmp_path / "snapshot_topic_bank.yaml").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid file extension"):
        get_input_file_type(tmp_path)


def test_update_bank_rejects_non_string_keys():
    model = ROSModel({BankType.SERVICE: ServiceBank()})

    with pytest.raises(KeyError, match="All keys must be strings"):
        model.update_bank(BankType.SERVICE, {123: Service(name="/demo_service")})


def test_update_bank_rejects_wrong_entity_type():
    model = ROSModel({BankType.SERVICE: ServiceBank()})

    with pytest.raises(ValueError, match="All values must be 'Service'"):
        model.update_bank(
            BankType.SERVICE, {"/demo_service": Action(name="/demo_action")}
        )


def test_read_model_from_yaml_roundtrip_preserves_multi_path_node_specs(tmp_path):
    model = make_full_model()
    model.node_specification_bank["demo_pkg/demo_node"].update_attributes(
        package="demo_pkg",
        file_path=["/real/demo_node", "/link/demo_node"],
    )

    model.save_model_yaml_files(tmp_path, "snapshot")
    loaded_model = ROSModel.read_model_from_yaml(tmp_path, "snapshot", spec_only=True)

    assert loaded_model.node_specification_bank["demo_pkg/demo_node"].file_path == [
        "/real/demo_node",
        "/link/demo_node",
    ]


@pytest.mark.parametrize(
    ("save_method", "load_method"),
    [
        ("save_model_json_files", "read_model_from_json"),
        ("save_model_yaml_files", "read_model_from_yaml"),
    ],
)
def test_service_membership_roundtrip_preserves_client_and_provider_names(
    tmp_path, save_method, load_method
):
    model = make_full_model()
    model.service_bank["/demo_service"].update_attributes(
        construct_type="std_srvs/srv/Empty",
        service_client_node_names={"/client"},
        service_provider_node_names={"/server"},
    )

    getattr(model, save_method)(tmp_path, "snapshot")
    loaded_model = getattr(ROSModel, load_method)(tmp_path, "snapshot")

    assert set(
        loaded_model.service_bank["/demo_service"].service_client_node_names
    ) == {"/client"}
    assert set(
        loaded_model.service_bank["/demo_service"].service_provider_node_names
    ) == {"/server"}


@pytest.mark.parametrize(
    ("save_method", "load_method"),
    [
        ("save_model_json_files", "read_model_from_json"),
        ("save_model_yaml_files", "read_model_from_yaml"),
    ],
)
def test_topic_roundtrip_preserves_ambiguous_metadata_shapes(
    tmp_path, save_method, load_method
):
    model = make_full_model()
    model.topic_bank["/chatter"].update_attributes(
        construct_type="std_msgs/msg/String",
        publisher_node_names={"/talker"},
        subscriber_node_names={"/listener"},
        endpoint_type="[multiple] PUBLISHER | SUBSCRIPTION",
        topic_hash="[multiple] hash-a | hash-b",
        qos_profile={
            "[multiple]": [
                {
                    "deadline": "0",
                    "depth": 10,
                    "durability": "VOLATILE",
                    "history": "KEEP_LAST",
                    "lifespan": "0",
                    "liveliness": "AUTOMATIC",
                    "liveliness_lease_duration": "0",
                    "reliability": "RELIABLE",
                },
                {
                    "deadline": "0",
                    "depth": 5,
                    "durability": "VOLATILE",
                    "history": "KEEP_LAST",
                    "lifespan": "0",
                    "liveliness": "AUTOMATIC",
                    "liveliness_lease_duration": "0",
                    "reliability": "BEST_EFFORT",
                },
            ]
        },
    )

    getattr(model, save_method)(tmp_path, "snapshot")
    loaded_model = getattr(ROSModel, load_method)(tmp_path, "snapshot")

    topic = loaded_model.topic_bank["/chatter"]
    assert topic.endpoint_type == "[multiple] PUBLISHER | SUBSCRIPTION"
    assert topic.topic_hash == "[multiple] hash-a | hash-b"
    assert topic.qos_profile == {
        "[multiple]": [
            {
                "deadline": "0",
                "depth": 10,
                "durability": "VOLATILE",
                "history": "KEEP_LAST",
                "lifespan": "0",
                "liveliness": "AUTOMATIC",
                "liveliness_lease_duration": "0",
                "reliability": "RELIABLE",
            },
            {
                "deadline": "0",
                "depth": 5,
                "durability": "VOLATILE",
                "history": "KEEP_LAST",
                "lifespan": "0",
                "liveliness": "AUTOMATIC",
                "liveliness_lease_duration": "0",
                "reliability": "BEST_EFFORT",
            },
        ]
    }


def test_read_model_from_pickle_roundtrip_preserves_service_and_action_membership(
    tmp_path,
):
    model = make_full_model()
    model.action_bank["/demo_action"].update_attributes(
        construct_type="demo_msgs/action/Demo",
        client_node_names={"/client"},
        server_node_names={"/server"},
    )
    model.service_bank["/demo_service"].update_attributes(
        construct_type="std_srvs/srv/Empty",
        service_client_node_names={"/client"},
        service_provider_node_names={"/server"},
    )

    model.save_model_pickle_files(tmp_path, "snapshot")
    loaded_model = ROSModel.read_model_from_pickle(tmp_path, "snapshot")

    assert set(loaded_model.action_bank["/demo_action"].client_node_names) == {
        "/client"
    }
    assert set(loaded_model.action_bank["/demo_action"].server_node_names) == {
        "/server"
    }
    assert set(
        loaded_model.service_bank["/demo_service"].service_client_node_names
    ) == {"/client"}
    assert set(
        loaded_model.service_bank["/demo_service"].service_provider_node_names
    ) == {"/server"}
