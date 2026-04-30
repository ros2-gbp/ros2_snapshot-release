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
# limitations under the License."""Metamodels used to model ROS Machines and the Banks that contain them."""

from typing import ClassVar, List, Optional, Set, Union

from ros2_snapshot.core.base_metamodel import _BankMetamodel, _EntityMetamodel


class Machine(_EntityMetamodel):
    """Metamodel for ROS Machines."""

    yaml_tag: ClassVar[str] = "!Machine"

    hostname: Optional[str] = None
    machine_id: Optional[str] = None
    machine_id_source: Optional[str] = None
    ip_address: Optional[str] = None
    node_names: Optional[Union[Set[str], List[str]]] = None


class MachineBank(_BankMetamodel):
    """Metamodel for Bank of ROS Machines."""

    yaml_tag: ClassVar[str] = "!MachineBank"
    HUMAN_OUTPUT_NAME = "Machines:"

    def _create_entity(self, name):
        """
        Create instance of named entity given bank type.

        :return: instance of entity
        """
        return Machine(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return Machine
