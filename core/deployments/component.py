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

"""Metamodels used to model ROS Nodelets and the Banks that contain them."""

from typing import ClassVar, Optional

from core.metamodels import Node


class Component(Node):
    """Metamodel for ROS Components."""

    yaml_tag: ClassVar[str] = "!Component"

    manager_node_name: Optional[str] = None

    def __init__(self, **kwargs):
        """Initialize the Nodelet metamodel."""
        super().__init__(**kwargs)
        self.manager_node_name = kwargs.get("manager_node_name", None)

    def set_manager_node(self, node):
        """Set manager mode for component."""
        self.manager_node_name = node
