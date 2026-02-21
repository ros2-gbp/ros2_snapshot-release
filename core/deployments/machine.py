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

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class Machine(_EntityMetamodel):
    """Metamodel for ROS Machines."""

    yaml_tag: ClassVar[str] = "!Machine"

    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    node_names: Optional[Union[Set[str], List[str]]] = None

    def __init__(self, **kwargs):
        """Initialize the Machine metamodel."""
        super().__init__(**kwargs)
        self.hostname = kwargs.get("hostname", None)
        self.ip_address = kwargs.get("ip_address", None)
        self.node_names = kwargs.get("node_names", None)


class MachineBank(_BankMetamodel):
    """Metamodel for Bank of ROS Machines."""

    yaml_tag: ClassVar[str] = "!MachineBank"
    HUMAN_OUTPUT_NAME = "Machines:"

    def __init__(self, **kwargs):
        """
        Construct a new instance of the Bank Metamodel from keyword arguments.

        :param kwargs: the keyword arguments
        :type kwargs: dict{str: str}
        :return: the constructed Bank Metamodel
        :rtype: ActionBank
        """
        super().__init__(**kwargs)

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
