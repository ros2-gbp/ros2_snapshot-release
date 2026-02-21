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

"""Metamodels used to model ROS Actions and the Banks that contain them."""

from typing import ClassVar, List, Optional, Union

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class Action(_EntityMetamodel):
    """Metamodel for ROS Actions."""

    yaml_tag: ClassVar[str] = "!Action"

    client_node_names: Optional[Union[str, List[str]]] = None
    construct_type: Optional[str] = None
    server_node_names: Optional[Union[str, List[str]]] = None

    def __init__(self, **kwargs):
        """Initialize the Action metamodel."""
        super().__init__(**kwargs)
        self.client_node_names = kwargs.get("client_node_names", None)
        self.construct_type = kwargs.get("construct_type", None)
        self.server_node_names = kwargs.get("server_node_names", None)

    def _add_graph_node_to_dot_graph(self, action_dot_name, graph):
        """
        Private helper method to add an Action DOT Node to the DOT Graph.

        Includes all of its Topic names.

        :param action_dot_name: the name of the Action's DOT Node
            to create
        :type action_dot_name: str
        :param graph: the current graph instance to add the Action's
            DOT Node to
        :type graph: graphviz.Digraph
        """
        action_dot_label_rows = ["<"]
        action_dot_label_rows.append('<TABLE BORDER="0" CELLBORDER="0">')
        action_dot_label_rows.append(f"<TR><TD>{self.name}</TD></TR>")
        action_dot_label_rows.append("<TR><TD>")
        action_dot_label_rows.append('<FONT POINT-SIZE="6">')
        action_dot_label_rows.append(
            '<TABLE CELLBORDER="0" CELLPADDING="0" BGCOLOR="GRAY" COLOR="BLACK">'
        )
        action_dot_label_rows.append("<TR><TD><U>action topics:</U></TD></TR>")
        action_dot_label_rows.append("</TABLE>")
        action_dot_label_rows.append("</FONT>")
        action_dot_label_rows.append("</TD></TR>")
        action_dot_label_rows.append("</TABLE>")
        action_dot_label_rows.append(">")
        action_dot_label = "\n".join(action_dot_label_rows)
        graph.node(action_dot_name, action_dot_label, shape="rectangle", color="purple")

    def _add_graph_edges_to_dot_graph(self, action_dot_name, graph):
        """
        Add the DOT Edges between an Action DOT Node and ROS Node DOT Nodes.

        This is based on whether the ROS Nodes are Action Servers or
        Clients for the Action

        :param action_dot_name: the Action's DOT Node name
        :type action_dot_name: str
        :param graph: the current graph instance to add the Action's
            DOT Edges to
        :type graph: graphviz.Digraph
        """
        for client_name in sorted(self.client_node_names):
            graph.edge(
                f"node-{client_name}",
                action_dot_name,
                arrowhead="vee",
                arrowsize="2",
                weight="1",
                penwidth="3",
                color="purple",
            )
        for server_name in sorted(self.server_node_names):
            graph.edge(
                action_dot_name,
                f"node-{server_name}",
                arrowhead="vee",
                arrowsize="2",
                weight="1",
                penwidth="3",
                color="purple",
            )

    def add_to_dot_graph(self, graph):
        """
        Add the ROS Entity to a DOT Graph.

        :param graph: the DOT Graph to add the ROS Entity to
        :type graph: graphviz.Digraph
        """
        action_dot_name = f"action-{self.name}"
        self._add_graph_node_to_dot_graph(action_dot_name, graph)
        self._add_graph_edges_to_dot_graph(action_dot_name, graph)


class ActionBank(_BankMetamodel):
    """Metamodel for Bank of ROS Actions."""

    yaml_tag: ClassVar[str] = "!ActionBank"
    HUMAN_OUTPUT_NAME = "Actions:"

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
        return Action(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return Action
