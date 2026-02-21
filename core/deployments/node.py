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


class Node(_EntityMetamodel):
    """Metamodel for ROS Nodes."""

    yaml_tag: ClassVar[str] = "!Node"

    node: Optional[str] = None
    namespace: Optional[str] = None
    executable_name: Optional[str] = None
    executable_file: Optional[str] = None
    cmdline: Optional[Union[str, List[str]]] = None
    num_threads: Optional[Union[str, int]] = None
    cpu_percent: Optional[Union[str, float]] = None
    memory_percent: Optional[Union[str, float]] = None
    memory_info: Optional[str] = None
    action_servers: Optional[Union[Dict[str, str], List[str]]] = None
    action_clients: Optional[Union[Dict[str, str], List[str]]] = None
    published_topic_names: Optional[Union[List[str], Dict[str, str]]] = None
    subscribed_topic_names: Optional[Union[List[str], Dict[str, str]]] = None
    provided_services: Optional[Union[List[str], Dict[str, str]]] = None
    parameter_names: Optional[List[str]]

    def __init__(self, **kwargs):
        """Initialize the Node metamodel."""
        super().__init__(**kwargs)
        self.node = kwargs.get("node", None)
        self.namespace = kwargs.get("namespace", None)
        self.executable_name = kwargs.get("executable_name", None)
        self.executable_file = kwargs.get("executable_file", None)
        self.cmdline = kwargs.get("cmdline", None)
        self.num_threads = kwargs.get("num_threads", None)
        self.cpu_percent = kwargs.get("cpu_percent", None)
        self.memory_percent = kwargs.get("memory_percent", None)
        self.memory_info = kwargs.get("memory_info", None)
        self.action_servers = kwargs.get("action_servers", None)
        self.action_clients = kwargs.get("action_clients", None)
        self.published_topic_names = kwargs.get("published_topic_names", None)
        self.subscribed_topic_names = kwargs.get("subscribed_topic_names", None)
        self.provided_services = kwargs.get("provided_services", None)
        self.parameter_names = kwargs.get("parameter_names", None)

    def add_to_dot_graph(self, graph):
        """
        Add the ROS Entity to a DOT Graph.

        :param graph: the DOT Graph to add the ROS Entity to
        :type graph: graphviz.Digraph
        """
        graph.node(f"node-{self.name}", self.name, color="blue")

    @staticmethod
    def _add_categorized_topic_information_to_rows_string(
        rows, topics, status, category
    ):
        """
        Add categorized Topic information to a collection of rows of strings.

        :param rows: the rows of strings to add to
        :type rows: list[str]
        :param topics: the names of Topics to add to the rows
        :type topics: set{str}
        :param status: the status of the Topics (e.g. 'published' or
            'subscribed')
        :type status: str
        :param category: the category to further describe the Topics
        :type category: str
        :return: the same rows, appended to with Topic information
        :rtype: list[str]
        """
        rows.append(f"        {status} {category} topics:")
        for topic in sorted(topics):
            rows.append(f'            - "{topic}"')
        return rows


class NodeBank(_BankMetamodel):
    """Metamodel for Bank of ROS Nodes."""

    yaml_tag: ClassVar[str] = "!NodeBank"
    HUMAN_OUTPUT_NAME = "Nodes:"

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
        return Node(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return Node
