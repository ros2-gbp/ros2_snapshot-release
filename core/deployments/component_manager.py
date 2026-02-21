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

from typing import ClassVar, List, Optional

from core.metamodels import Node


class ComponentManager(Node):
    """Metamodel for ROS Component Nodes."""

    yaml_tag: ClassVar[str] = "!ComponentManager"

    components: Optional[List[str]] = None

    def __init__(self, **kwargs):
        """Initialize the Component Node metamodel."""
        super().__init__(**kwargs)
        self.components = kwargs.get("components", None)

    def add_components_list(self, comp_list):
        """
        Set our component list.

        :param comp_list: list of components
        """
        self.components = comp_list

    def add_to_dot_graph(self, graph):
        """
        Add the ROS Entity to a DOT Graph.

        :param graph: the DOT Graph to add the ROS Entity to
        :type graph: graphviz.Digraph
        """
        graph.node(f"component_node-{self.name}", self.name, color="blue")
