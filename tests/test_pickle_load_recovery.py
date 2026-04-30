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

from ros2_snapshot.core.ros_model import ROSModel


def test_read_model_from_pickle_recovers_from_empty_bank_file(tmp_path):
    (tmp_path / "snapshot_node_bank.pkl").write_bytes(b"")

    model = ROSModel.read_model_from_pickle(tmp_path, "snapshot")

    assert model.node_bank.keys == []
