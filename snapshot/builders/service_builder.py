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
Module for ServiceBuilder.

*EntityBuilders, which represent ROS Entities and are
responsible for allowing themselves to be populated with basic
information and then further populating themselves from that
information for the purpose of extracting metamodel instances
"""

from core.metamodels import Service
from core.utilities import filters

from ros2cli.node.strategy import NodeStrategy

from ros2service.api import get_service_names_and_types

from snapshot.builders.base_builders import _EntityBuilder


class ServiceBuilder(_EntityBuilder):
    """
    Define a ServiceBuilder.

    Represents a ROS
    Service and is responsible for allowing itself to be
    populated with basic information relevant to a Service and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    def __init__(self, name):
        """
        Instantiate an instance of the ServiceBuilder.

        :param name: the name of the Service that this ServiceBuilder
            represents
        :type name: str
        """
        super(ServiceBuilder, self).__init__(name)
        self._arguments = None
        self._service_provider_node_names = set()

    @property
    def construct_type(self):
        """
        Return the Service's ROS type.

        :return: the Service's ROS type
        :rtype: str
        """
        with NodeStrategy(None) as node:
            self.services_type = {}
            srv_name_and_types = get_service_names_and_types(
                node=node, include_hidden_services=True
            )
            for service in srv_name_and_types:
                self.services_type[service[0]] = service[1][0]

        return self.services_type[self.name]

    @property
    def service_provider_node_names(self):
        """
        Return the names of the ROS Nodes that act as Providers.

        :return: the names of the Service Provider ROS Nodes
        :rtype: set{str}
        """
        node_filter = filters.NodeFilter.get_filter()
        return list(
            {
                name
                for name in self._service_provider_node_names
                if not node_filter.should_filter_out(name)
            }
        )

    def add_service_provider_node_name(self, service_provider_node_name):
        """
        Add service provider node name.

        Adds an association between a Service Provider ROS Node's name
        and this Action

        :param service_provider_node_name: the Service Provider ROS
            Node name to associate with this Action
        :type service_provider_node_name: str
        """
        self._service_provider_node_names.add(service_provider_node_name)

    def extract_metamodel(self):
        """
        Extract metamodel.

        Allows the ServiceBuilder to create / extract a Service
        instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: Service
        """
        service_metamodel = Service(
            source="ros_snapshot",
            name=self.name,
            construct_type=self.construct_type,
            service_provider_node_names=self.service_provider_node_names,
        )
        return service_metamodel
