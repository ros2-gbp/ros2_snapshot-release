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

from ros2_snapshot.core.metamodels import Topic
from ros2_snapshot.core.base_metamodel import ValidationError
from ros2_snapshot.core.utilities import filters
from ros2_snapshot.core.utilities.logger import Logger, LoggerLevel

from ros2_snapshot.snapshot.builders.base_builders import _EntityBuilder

_UNSET = object()


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
        self._qos_profiles = {}
        self._gid_information = {}
        self._topic_hashes = set()
        self._topic_hash_cache = _UNSET
        self._qos_profile_cache = _UNSET

    @staticmethod
    def _serialize_qos_profile(qos_profile):
        """Serialize a QoS profile into a deterministic dictionary."""
        return {
            "durability": str(qos_profile.durability),
            "deadline": str(qos_profile.deadline),
            "liveliness": str(qos_profile.liveliness),
            "liveliness_lease_duration": str(qos_profile.liveliness_lease_duration),
            "reliability": str(qos_profile.reliability),
            "lifespan": str(qos_profile.lifespan),
            "history": str(qos_profile.history),
            "depth": qos_profile.depth,
        }

    @staticmethod
    def _qos_profile_key(qos_profile):
        """Return a QoS comparison key, ignoring endpoint-local queue depth."""
        comparable_profile = dict(qos_profile)
        comparable_profile.pop("depth", None)
        return str(sorted(comparable_profile.items()))

    @staticmethod
    def _merge_qos_depth(existing_profile, qos_profile):
        """Merge depth-only QoS differences into one profile."""
        existing_depth = existing_profile["depth"]
        new_depth = qos_profile["depth"]
        if existing_depth == new_depth:
            return existing_profile

        if isinstance(existing_depth, list):
            depths = set(existing_depth)
        else:
            depths = {existing_depth}
        depths.add(new_depth)

        merged_profile = dict(existing_profile)
        merged_profile["depth"] = sorted(depths)
        return merged_profile

    def _normalize_metadata_values(self, metadata_name, values):
        """Return a deterministic scalar metadata value or an explicit ambiguity marker."""
        if not values:
            return None

        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return sorted_values[0]

        ambiguous_value = f"[multiple] {' | '.join(sorted_values)}"
        Logger.get_logger().log(
            LoggerLevel.WARNING,
            (
                f"Topic '{self.name}' has multiple {metadata_name} values; "
                f"recording ambiguity as '{ambiguous_value}'."
            ),
        )
        return ambiguous_value

    def _normalize_qos_profiles(self):
        """Return a deterministic QoS profile or an explicit ambiguity structure."""
        if not self._qos_profiles:
            return {}

        profiles = sorted(
            self._qos_profiles.values(),
            key=lambda profile: str(sorted(profile.items())),
        )
        if len(profiles) == 1:
            return profiles[0]

        Logger.get_logger().log(
            LoggerLevel.WARNING,
            (
                f"Topic '{self.name}' has multiple QoS profiles; "
                "recording all observed profiles explicitly."
            ),
        )
        return {"[multiple]": profiles}

    def get_verbose_info(self, info, gid_dict):
        """Add verbose information to the topic_bank."""
        self._node_name = info.node_name
        qos_profile = self._serialize_qos_profile(info.qos_profile)
        qos_profile_key = self._qos_profile_key(qos_profile)
        existing_profile = self._qos_profiles.get(qos_profile_key)
        if existing_profile is None:
            self._qos_profiles[qos_profile_key] = qos_profile
        else:
            self._qos_profiles[qos_profile_key] = self._merge_qos_depth(
                existing_profile, qos_profile
            )
        self._gid_information = "".join(
            format(byte, "02x") for byte in info.endpoint_gid
        )
        gid_dict[info.node_name] = self._gid_information
        self.set_gid_dict(gid_dict)
        self._topic_hashes.add(str(info.topic_type_hash))
        self._topic_hash_cache = _UNSET
        self._qos_profile_cache = _UNSET

    def set_gid_dict(self, gid_dict):
        """Set GID information."""
        self._gid_information = gid_dict

    @property
    def qos_profile(self):
        """Get QOS profile."""
        if self._qos_profile_cache is _UNSET:
            self._qos_profile_cache = self._normalize_qos_profiles()
        return self._qos_profile_cache

    @property
    def gid_information(self):
        """Get GID information."""
        return self._gid_information

    @property
    def topic_hash(self):
        """Get topic hash."""
        if self._topic_hash_cache is _UNSET:
            self._topic_hash_cache = self._normalize_metadata_values(
                "topic_hash", self._topic_hashes
            )
        return self._topic_hash_cache

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
                topic_hash=self.topic_hash,
            )
            return topic_metamodel
        except ValidationError as exc:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                f"Topic builder extract_metamodel: Pydantic Validation Error:\n    {exc}\n"
                f"    name:'{self.name}'\n"
                f"    construct_type:'{self.construct_type}'\n"
                f"    publisher_node_names:'{self.publisher_node_names}'\n"
                f"    subscriber_node_names:'{self.subscriber_node_names}'",
            )
            raise exc
