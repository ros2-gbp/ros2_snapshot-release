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

from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.deployments.action import ActionBank
from ros2_snapshot.core.deployments.machine import MachineBank
from ros2_snapshot.core.deployments.node import NodeBank
from ros2_snapshot.core.deployments.parameter import ParameterBank
from ros2_snapshot.core.deployments.service import ServiceBank
from ros2_snapshot.core.deployments.topic import TopicBank


def test_action_json_roundtrip_handles_set_fields(tmp_path):
    model = ROSModel(
        {
            BankType.NODE: NodeBank(),
            BankType.TOPIC: TopicBank(),
            BankType.ACTION: ActionBank(),
            BankType.SERVICE: ServiceBank(),
            BankType.PARAMETER: ParameterBank(),
            BankType.MACHINE: MachineBank(),
        }
    )

    model.action_bank["/demo_action"].update_attributes(
        construct_type="demo_msgs/action/Demo",
        client_node_names={"/client"},
        server_node_names={"/server"},
    )

    model.save_model_json_files(tmp_path, "snapshot")
    loaded_model = ROSModel.read_model_from_json(tmp_path, "snapshot")

    action = loaded_model.action_bank["/demo_action"]
    assert set(action.client_node_names) == {"/client"}
    assert set(action.server_node_names) == {"/server"}


def test_action_yaml_roundtrip_handles_set_fields(tmp_path):
    model = ROSModel(
        {
            BankType.NODE: NodeBank(),
            BankType.TOPIC: TopicBank(),
            BankType.ACTION: ActionBank(),
            BankType.SERVICE: ServiceBank(),
            BankType.PARAMETER: ParameterBank(),
            BankType.MACHINE: MachineBank(),
        }
    )

    model.action_bank["/demo_action"].update_attributes(
        construct_type="demo_msgs/action/Demo",
        client_node_names={"/client"},
        server_node_names={"/server"},
    )

    model.save_model_yaml_files(tmp_path, "snapshot")
    loaded_model = ROSModel.read_model_from_yaml(tmp_path, "snapshot")

    action = loaded_model.action_bank["/demo_action"]
    assert set(action.client_node_names) == {"/client"}
    assert set(action.server_node_names) == {"/server"}
