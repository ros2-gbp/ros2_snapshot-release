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
from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.core.specifications.type_specification import TypeSpecificationBank


def test_type_specification_json_roundtrip_preserves_multiple_file_paths(tmp_path):
    model = ROSModel(
        {
            BankType.PACKAGE_SPECIFICATION: PackageSpecificationBank(),
            BankType.NODE_SPECIFICATION: NodeSpecificationBank(),
            BankType.MESSAGE_SPECIFICATION: TypeSpecificationBank(),
            BankType.SERVICE_SPECIFICATION: TypeSpecificationBank(),
            BankType.ACTION_SPECIFICATION: TypeSpecificationBank(),
        }
    )

    model.message_specification_bank["demo_pkg/Demo"].update_attributes(
        construct_type="msg",
        package="demo_pkg",
        file_path=["/real/Demo.msg", "/link/Demo.msg"],
        spec="string data",
    )

    model.save_model_json_files(tmp_path, "snapshot")
    loaded_model = ROSModel.read_model_from_json(tmp_path, "snapshot", spec_only=True)

    assert loaded_model.message_specification_bank["demo_pkg/Demo"].file_path == [
        "/real/Demo.msg",
        "/link/Demo.msg",
    ]
