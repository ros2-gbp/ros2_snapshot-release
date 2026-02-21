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

"""Metamodels used to model ROS Nodes and the Banks that contain them."""

from typing import ClassVar, Dict, List, Optional, Union

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class NodeSpecification(_EntityMetamodel):
    """Metamodel for ROS Node specifications."""

    yaml_tag: ClassVar[str] = "!NodeSpecification"

    source: Optional[Union[str, List[str]]] = None
    action_clients: Optional[Union[List[str], Dict[str, str]]] = None
    action_servers: Optional[Union[List[str], Dict[str, str]]] = None
    file_path: Optional[str] = None
    package: Optional[str] = None
    parameters: Optional[Union[List[str], Dict[str, str]]] = None
    published_topics: Optional[Union[List[str], Dict[str, str]]] = None
    subscribed_topics: Optional[Union[List[str], Dict[str, str]]] = None
    services_provided: Optional[Union[List[str], Dict[str, str]]] = None
    validated: bool = False

    def __init__(self, **kwargs):
        """Initialize the Node specification."""
        super().__init__(**kwargs)
        self.action_clients = kwargs.get("action_clients", None)
        self.action_servers = kwargs.get("action_servers", None)
        self.file_path = kwargs.get("file_path", None)
        self.package = kwargs.get("package", None)
        self.parameters = kwargs.get("parameters", None)
        self.published_topics = kwargs.get("published_topics", None)
        self.subscribed_topics = kwargs.get("subscribed_topics", None)
        self.services_provided = kwargs.get("services_provided", None)
        self.validated = kwargs.get("validated", False)


class NodeSpecificationBank(_BankMetamodel):
    """Metamodel for Bank of ROS Node specifications."""

    yaml_tag: ClassVar[str] = "!NodeSpecBank"
    HUMAN_OUTPUT_NAME: ClassVar[str] = "NodeSpecs:"

    def __init__(self, **kwargs):
        """
        Construct a new instance of the Bank Metamodel from keyword arguments.

        :param kwargs: the keyword arguments
        :type kwargs: dict{str: str}
        :return: the constructed Bank Metamodel
        :rtype: NodeBankMetamodel
        """
        super().__init__(**kwargs)

    def _create_entity(self, name):
        """
        Create instance of named entity given bank type.

        :return: instance of entity
        """
        return NodeSpecification(name=name)

    def entity_class(self, name):
        """
        Class of entity given bank type.

        :return: instance of entity class definition
        """
        return NodeSpecification
