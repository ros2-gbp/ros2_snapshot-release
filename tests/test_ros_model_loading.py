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

import os

from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.core.specifications.type_specification import TypeSpecificationBank
from ros2_snapshot.snapshot.snapshot import ROSSnapshot


def make_spec_model():
    package_bank = PackageSpecificationBank()
    package_bank["demo_pkg"].update_attributes(package_version="1.0.0")

    node_bank = NodeSpecificationBank()
    node_bank["demo_pkg/demo_node"].update_attributes(
        package="demo_pkg",
        file_path="/tmp/demo_node",
    )

    return ROSModel(
        {
            BankType.PACKAGE_SPECIFICATION: package_bank,
            BankType.NODE_SPECIFICATION: node_bank,
            BankType.MESSAGE_SPECIFICATION: TypeSpecificationBank(),
            BankType.SERVICE_SPECIFICATION: TypeSpecificationBank(),
            BankType.ACTION_SPECIFICATION: TypeSpecificationBank(),
        }
    )


def remove_partial_spec_files(directory_path, base_file_name):
    for bank_name in (
        "message_specification_bank",
        "service_specification_bank",
        "action_specification_bank",
    ):
        os.remove(os.path.join(directory_path, f"{base_file_name}_{bank_name}.json"))


def test_read_model_from_json_uses_empty_banks_for_missing_spec_files(tmp_path):
    model = make_spec_model()
    model.save_model_json_files(tmp_path, "snapshot")
    remove_partial_spec_files(tmp_path, "snapshot")

    loaded_model = ROSModel.read_model_from_json(tmp_path, "snapshot", spec_only=True)

    assert isinstance(
        loaded_model[BankType.MESSAGE_SPECIFICATION], TypeSpecificationBank
    )
    assert isinstance(
        loaded_model[BankType.SERVICE_SPECIFICATION], TypeSpecificationBank
    )
    assert isinstance(
        loaded_model[BankType.ACTION_SPECIFICATION], TypeSpecificationBank
    )
    assert loaded_model[BankType.MESSAGE_SPECIFICATION].keys == []
    assert loaded_model[BankType.SERVICE_SPECIFICATION].keys == []
    assert loaded_model[BankType.ACTION_SPECIFICATION].keys == []


def test_load_specifications_handles_partial_json_without_attribute_error(tmp_path):
    model = make_spec_model()
    model.save_model_json_files(tmp_path, "snapshot")
    remove_partial_spec_files(tmp_path, "snapshot")

    ros_snapshot = ROSSnapshot()

    assert ros_snapshot.load_specifications(tmp_path) is False
    assert isinstance(
        ros_snapshot.message_specification_bank,
        TypeSpecificationBank,
    )
    assert isinstance(
        ros_snapshot.service_specification_bank,
        TypeSpecificationBank,
    )
    assert isinstance(
        ros_snapshot.action_specification_bank,
        TypeSpecificationBank,
    )
