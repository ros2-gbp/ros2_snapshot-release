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
Module for TopicBuilder.

*EntityBuilders, which represent ROS Entities and are
responsible for allowing themselves to be populated with basic
information and then further populating themselves from that
information for the purpose of extracting metamodel instances
"""

from core.metamodels import Topic
from core.utilities import filters

from pydantic.error_wrappers import ValidationError

from rclpy.endpoint_info import EndpointTypeEnum

from snapshot.builders.base_builders import _EntityBuilder


class TopicBuilder(_EntityBuilder):
    """
    Define a TopicBuilder.

    Represents a ROS
    Topic and is responsible for allowing itself to be
    populated with basic information relevant to a Topic and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    def __init__(self, name):
        """
        Instantiate an instance of the TopicBuilder.

        :param name: the name of the Topic that this TopicBuilder
            represents
        :type name: str
        """
        super(TopicBuilder, self).__init__(name)
        self._construct_type = None
        self._node_names = {"published": set(), "subscribed": set()}
        self._qos_profile = {}
        self._gid_information = {}
        self._topic_hash = None
        self._endpoint_type = None

    def get_verbose_info(self, info, gid_dict):
        """Add verbose information to the topic_bank."""
        self._node_name = info.node_name
        qos_profile = info.qos_profile
        self._qos_profile = {
            "durability": str(qos_profile.durability),
            "deadline": str(qos_profile.deadline),
            "liveliness": str(qos_profile.liveliness),
            "liveliness_lease_duration": str(qos_profile.liveliness_lease_duration),
            "reliability": str(qos_profile.reliability),
            "lifespan": str(qos_profile.lifespan),
            "history": str(qos_profile.history),
            "depth": qos_profile.depth,
        }
        self._gid_information = "".join(
            format(byte, "02x") for byte in info.endpoint_gid
        )
        gid_dict[info.node_name] = self._gid_information
        self.set_gid_dict(gid_dict)
        self._endpoint_type = info.endpoint_type
        self._topic_hash = str(info.topic_type_hash)

    def set_gid_dict(self, gid_dict):
        """Set GID information."""
        self._gid_information = gid_dict

    @property
    def qos_profile(self):
        """Get QOS profile."""
        return self._qos_profile

    @property
    def gid_information(self):
        """Get GID information."""
        return self._gid_information

    @property
    def topic_hash(self):
        """Get topic hash."""
        return self._topic_hash

    @property
    def endpoint_type(self):
        """Get endpoint type."""
        if self._endpoint_type == EndpointTypeEnum.PUBLISHER:
            return "PUBLISHER"
        elif self._endpoint_type == EndpointTypeEnum.SUBSCRIPTION:
            return "SUBSCRIPTION"
        elif self._endpoint_type == EndpointTypeEnum.CLIENT:
            return "CLIENT"
        elif self._endpoint_type == EndpointTypeEnum.SERVER:
            return "SERVER"
        else:
            return "UNKNOWN"

    @property
    def construct_type(self):
        """
        Return this Topic's ROS type.

        :return: this Topic's ROS type
        :rtype: str
        """
        return self._construct_type

    @construct_type.setter
    def construct_type(self, construct_type):
        """
        Set this Topic's ROS type.

        :param construct_type: the Topic's ROS type
        :type construct_type: str
        """
        self._construct_type = construct_type

    @property
    def publisher_node_names(self):
        """
        Return the names of the ROS Nodes that have Published the Topic.

        :return: the names of Publisher ROS Nodes for this Topic
        :rtype: set{str}
        """
        node_filter = filters.NodeFilter.get_filter()

        return list(
            {
                name
                for name in self._node_names["published"]
                if not node_filter.should_filter_out(name)
            }
        )

    @property
    def subscriber_node_names(self):
        """
        Return the names of the subscribed ROS Nodes.

        :return: the names of Subscriber ROS Nodes for this Topic
        :rtype: set{str}
        """
        node_filter = filters.NodeFilter.get_filter()

        return list(
            {
                name
                for name in self._node_names["subscribed"]
                if not node_filter.should_filter_out(name)
            }
        )

    def add_node_name(self, node_name, status):
        """
        Associate this Topic with a ROS Node name.

        Based on whether it
        was Published by or Subscribed to by the ROS Node

        :param node_name: the name of the associated ROS Node
        :type node_name: str
        :param status: the status or relationship ('published' or
            'subscribed') between the Topic and the ROS Node
        :type status: str
        """
        self._node_names[status].add(node_name)

    def extract_metamodel(self):
        """
        Extract metamodel.

        Allows the TopicBuilder to create / extract a Topic
        instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: Topic
        """
        try:
            topic_metamodel = Topic(
                source="ros_snapshot",
                name=self.name,
                construct_type=self.construct_type,
                publisher_node_names=self.publisher_node_names,
                subscriber_node_names=self.subscriber_node_names,
                qos_profile=self.qos_profile,
                endpoint_type=self.endpoint_type,
                topic_hash=self.topic_hash,
            )
            return topic_metamodel
        except ValidationError as exc:
            print(
                f"Topic builder extract_metamodel: Pydantic Validation Error :\n    {exc}",
                flush=True,
            )
            print(f"    name:'{self.name}'")
            print(f"    construct_type:'{self.construct_type}'")
            print(f"    publisher_node_names:'{self.publisher_node_names}'")
            print(
                f"    subscriber_node_names:'{self.subscriber_node_names}'", flush=True
            )
            raise exc
