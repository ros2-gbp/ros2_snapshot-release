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

"""
Module for ParameterBuilder.

Represent ROS Entities and are
responsible for allowing themselves to be populated with basic
information and then further populating themselves from that
information for the purpose of extracting metamodel instances
"""

from core.metamodels import Parameter

from snapshot.builders.base_builders import _EntityBuilder


class ParameterBuilder(_EntityBuilder):
    """
    Define a ParameterBuilder.

    Represents a ROS
    Parameter and is responsible for allowing itself to be
    populated with basic information relevant to a Parameter and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    def __init__(self, name):
        """
        Instantiate an instance of the ParameterBuilder.

        :param name: the name of the Parameter that this
            ParameterBuilder represents
        :type name: str
        """
        super(ParameterBuilder, self).__init__(name)
        self._param_val = None
        self._node_name = None
        self._description = None

    def add_info(self, parameter_info):
        """Collect information and initializes each parameter in the bank."""
        self._name, self._param_val, self._node_name = parameter_info

    def add_description(self, descriptor):
        """Collect description information associated with the parameter."""
        self._description = descriptor.description

    @property
    def description(self):
        """
        Return the description associated with the parameter.

        :return: description
        :rtype: str
        """
        if self._description == "":
            return None
        return self._description

    @property
    def node_name(self):
        """
        Return the node name associated with the parameter.

        :return: node_name
        :rtype: str
        """
        return self._node_name

    @property
    def value(self):
        """
        Return the value of the Parameter.

        :return: the value of the Parameter
        :rtype: str
        """
        return self._param_val

    @property
    def value_type(self):
        """
        Return the Python type of the Parameter's value.

        :return: the Python type of the Parameter's value
        :rtype: str
        """
        return (
            str(type(self.value))
            .replace("<", "")
            .replace(">", "")
            .replace("type", "")
            .replace("'", "")
            .strip()
        )

    @property
    def construct_type(self):
        """
        Return the type of the Parameter's value.

        :return: the Python type of the Parameter's value
        :rtype: str
        """
        return self.value_type

    def extract_metamodel(self):
        """
        Extract Parameter metamodel.

        Allow the ParameterBuilder to create / extract a
        Parameter instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: Parameter
        """
        parameter_metamodel = Parameter(
            source="ros_snapshot",
            name=self.name,
            value_type=self.value_type,
            value=self.value,
            node=self.node_name,
            description=self.description,
        )
        return parameter_metamodel
