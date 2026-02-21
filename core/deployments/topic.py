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

"""Metamodels used to model ROS Topics and the Banks that contain them."""

from typing import Any, ClassVar, List, Optional, Set, Union

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class Topic(_EntityMetamodel):
    """Metamodel for ROS Topics."""

    yaml_tag: ClassVar[str] = "!Topic"

    construct_type: Optional[str] = None
    publisher_node_names: Optional[Union[Set[str], List[str]]] = None
    subscriber_node_names: Optional[Union[Set[str], List[str]]] = None
    qos_profile: Optional[Any] = None
    endpoint_type: Optional[str] = None
    topic_hash: Optional[str] = None

    def __init__(self, **kwargs):
        """Initialize the Nodelet metamodel."""
        super().__init__(**kwargs)
        self.construct_type = kwargs.get("construct_type", None)
        self.publisher_node_names = kwargs.get("publisher_node_names", None)
        self.subscriber_node_names = kwargs.get("subscriber_node_names", None)

    def add_to_dot_graph(self, graph):
        """
        Add the ROS Entity to a DOT Graph.

        :param graph: the DOT Graph to add the ROS Entity to
        :type graph: graphviz.Digraph
        """
        topic_dot_name = f"topic-{self.name}"
        topic_dot_label = self.name
        graph.node(topic_dot_name, topic_dot_label, shape="rectangle", color="red")
        for publisher_node_name in sorted(self.publisher_node_names):
            graph.edge(f"node-{publisher_node_name}", topic_dot_name)
        for subscriber_node_name in sorted(self.subscriber_node_names):
            graph.edge(topic_dot_name, f"node-{subscriber_node_name}")


class TopicBank(_BankMetamodel):
    """Metamodel for Bank of ROS Topics."""

    yaml_tag: ClassVar[str] = "!TopicBank"
    HUMAN_OUTPUT_NAME = "Topics:"

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
        return Topic(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return Topic
