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

"""Metamodels used to model ROS Parameters and the Banks that contain them."""

from typing import Any, ClassVar, Optional

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class Parameter(_EntityMetamodel):
    """Metamodel for ROS Parameters."""

    yaml_tag: ClassVar[str] = "!Parameter"

    value_type: Optional[str] = None
    value: Optional[Any] = None
    node: Optional[str] = None
    description: Optional[str] = None

    def __init__(self, **kwargs):
        """Initialize the Nodelet metamodel."""
        super().__init__(**kwargs)
        self.value_type = kwargs.get("value_type", None)
        self.value = kwargs.get("value", None)
        self.node = kwargs.get("node", None)
        self.description = kwargs.get("description", None)


class ParameterBank(_BankMetamodel):
    """Metamodel for Bank of ROS Parameters."""

    yaml_tag: ClassVar[str] = "!ParameterBank"
    HUMAN_OUTPUT_NAME = "Parameters:"

    def __init__(self, **kwargs):
        """
        Construct a new instance of the ParameterBank Metamodel from keyword arguments.

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
        return Parameter(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return Parameter
