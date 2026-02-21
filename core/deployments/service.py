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

"""Metamodels used to model ROS Services and the Banks that contain them."""

from typing import ClassVar, List, Optional, Set, Union

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class Service(_EntityMetamodel):
    """Metamodel for ROS Services."""

    yaml_tag: ClassVar[str] = "!Service"

    construct_type: Optional[str] = None
    service_provider_node_names: Optional[Union[Set[str], List[str]]] = None

    def __init__(self, **kwargs):
        """Initialize the Nodelet metamodel."""
        super().__init__(**kwargs)
        self.construct_type = kwargs.get("construct_type", None)
        self.service_provider_node_names = kwargs.get(
            "service_provider_node_names", None
        )


class ServiceBank(_BankMetamodel):
    """Metamodel for Bank of ROS Services."""

    yaml_tag: ClassVar[str] = "!ServiceBank"
    HUMAN_OUTPUT_NAME = "Services:"

    def __init__(self, **kwargs):
        """
        Construct a new instance of the ServiceBank Metamodel from keyword arguments.

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
        return Service(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return Service
