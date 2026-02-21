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
Module for *EntityBuilders.

EntityBuilders represent ROS Entities and are
responsible for allowing themselves to be populated with basic
information and then further populating themselves from that
information for the purpose of extracting metamodel instances
"""

from core.metamodels import Action
from core.utilities.logger import Logger, LoggerLevel

from snapshot.builders.base_builders import _EntityBuilder


class ActionBuilder(_EntityBuilder):
    """
    Define an ActionBuilder.

    ActionBuilder represents a ROS
    Action and is responsible for allowing itself to be
    populated with basic information relevant to an Action and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    CLIENT_PUBLISHED_TOPIC_SUFFIXES = {"/cancel", "/goal"}
    SERVER_PUBLISHED_TOPIC_SUFFIXES = {"/feedback", "/result", "/status"}
    TOPIC_SUFFIXES = CLIENT_PUBLISHED_TOPIC_SUFFIXES | SERVER_PUBLISHED_TOPIC_SUFFIXES
    NUM_TOPIC_SUFFIXES = len(TOPIC_SUFFIXES)
    CORE_TOPIC_SUFFIXES_TO_TYPE_TOKENS = {
        "/feedback": "Feedback",
        "/goal": "Goal",
        "/result": "Result",
    }

    def __init__(self, name):
        """
        Instantiate an instance of the ActionBuilder.

        :param name: the name of the Action that this ActionBuilder
            represents
        :type name: str
        """
        super(ActionBuilder, self).__init__(name)
        self._construct_type = None  # Set during validation
        self._topic_names_to_builders = {}
        self._topic_name_suffixes_to_builders = {}
        self._client_node_names = set()
        self._server_node_names = set()
        self._action_information = {}

    def add_info(self, action_information):
        """
        Collect information and sort it into respective attributes.

        :action_information: all known information about an action, including clients and servers
        """
        self._action_information = action_information
        self._client_node_names, self._server_node_names = self.get_node_info
        self._client_node_names = list(self._client_node_names)
        self._server_node_names = list(self._server_node_names)
        for elem in list(self._action_information["types"]):
            self._construct_type = elem

    @property
    def get_node_info(self):
        """
        Return this Action's ROS client / server information.

        :return: clients, servers
        :rtype: tuple(set(), set())
        """
        return self._action_information["clients"], self._action_information["servers"]

    @property
    def construct_type(self):
        """
        Return this Action's ROS type.

        :return: this Action's ROS type
        :rtype: str
        """
        return self._construct_type

    def prepare(self, **kwargs):
        """
        Prepare ActionBuilder internal state.

        for eventual metamodel extraction; internal changes to the state
        of the class instance occur here

        :param kwargs: keyword arguments used in the preparation process
        :type kwargs: dict{param: value}
        """
        for topic_builder in list(self.topic_names_to_builders.values()):
            topic_builder.prepare()

    @property
    def topic_names_to_builders(self):
        """
        Return the mapping of Topic names to TopicBuilders.

        TopicBuilders represent the Topics that are part of the Action

        :return: the mapping of Topic names to TopicBuilders
        :rtype: dict{str: TopicBuilder}
        """
        return self._topic_names_to_builders

    @property
    def topic_name_suffixes_to_builders(self):
        """
        Return the mapping of Topic name suffixes (last token) to TopicBuilders.

        TopicBuilders represent the Topics that are part of the Action

        :return: the mapping of Topic suffix names to TopicBuilders
        :rtype: dict{str: TopicBuilder}
        """
        return self._topic_name_suffixes_to_builders

    def add_topic_builder(self, topic_builder):
        """
        Add a TopicBuilder that represents the Topic.

        :param topic_builder: the TopicBuilder to add to the Action
        :type topic_builder: TopicBuilder
        """
        self._topic_names_to_builders[topic_builder.name] = topic_builder
        self._topic_name_suffixes_to_builders[topic_builder.name_suffix] = topic_builder

    @property
    def client_node_names(self):
        """
        Return the names of Client ROS Nodes for this Action.

        :return: the names of Client ROS Nodes for this Action
        :rtype: set{str}
        """
        return self._client_node_names

    @property
    def server_node_names(self):
        """
        Return the names of Server ROS Nodes for this Action.

        :return: the names of Server ROS Nodes for this Action
        :rtype: set{str}
        """
        return self._server_node_names

    def _count_action_node_appearances(
        self, publisher_suffixes, subscriber_suffixes, action_node_to_counts
    ):
        """
        Count the number of appearances or cases in suspected ROS Nodes.

        Look for nodes that act in either a Client or
        Server capacity, are found to Publish or Subscribe to Topics
        ending in the expected Topic suffixes

        :param publisher_suffixes: the expected suffixes to check for
            Published Topics by the ROS Nodes
        :type publisher_suffixes: set{str}
        :param subscriber_suffixes: the expected suffixes to check for
            Subscribed Topics by the ROS Nodes
        :type subscriber_suffixes: set{str}
        :param action_node_to_counts: the mapping of Action Server or
            Action Client ROS Node names to appearance counts
        :type action_node_to_counts: dict{str: int}
        """
        print("\x1b[92mcount_action_node_appearances\x1b[0m")
        print(
            f"\n\t self_topic_name_suffixes_to_builders: {self.topic_name_suffixes_to_builders}"
        )
        print(f"\t publisher_suffixes: {publisher_suffixes}")
        for suffix in publisher_suffixes:
            print(f"SUFFIX : {suffix}")
            topic_builder = self.topic_name_suffixes_to_builders[suffix]

            for action_node_name in topic_builder.publisher_node_names:
                ActionBuilder._add_or_increment_dictionary_count(
                    action_node_to_counts, action_node_name
                )
        for suffix in subscriber_suffixes:
            topic_builder = self.topic_name_suffixes_to_builders[suffix]
            for action_node_name in topic_builder.subscriber_node_names:
                ActionBuilder._add_or_increment_dictionary_count(
                    action_node_to_counts, action_node_name
                )

    @staticmethod
    def _add_or_increment_dictionary_count(counts_dictionary, key):
        """
        Add an entry for a given key or increment count.

        Use the integer value for an entry in a given dictionary of keys to
        counts

        :param counts_dictionary: the mapping of keys to integer counts
        :type counts_dictionary: dict{str: int}
        :param key: the key to add (value of 1) or to increment an entry
            for (by a value of 1)
        :type key: str
        """
        if key not in counts_dictionary:
            counts_dictionary[key] = 0
        counts_dictionary[key] += 1

    @staticmethod
    def _gather_valid_action_node_names_based_on_appearance_counts(
        action_node_names_to_counts,
    ):
        """
        Create a collection of valid ROS Node names.

        For nodes acting in either a Server or Client manner, based on how many
        appearances are found between expected Topics and the ROS Nodes
        Publishing or Subscribing to them

        :param action_node_names_to_counts: the mapping of ROS Node
            names to appearance counts
        :type action_node_names_to_counts: dict{str: int}
        :return: valid Action Server and Client ROS Node names
        :rtype: set{str}
        """
        valid_node_names = set()
        for node_name, appearance_count in list(action_node_names_to_counts.items()):
            if appearance_count == ActionBuilder.NUM_TOPIC_SUFFIXES:
                valid_node_names.add(node_name)
            else:
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Node name {node_name} for Action not valid as action client or server.",
                )
        return valid_node_names

    @classmethod
    def test_potential_action_topic_builder(cls, action_topic):
        """
        Verify whether a potential Action TopicBuilder has a name suffix.

        Checks if suffix that falls within the set of expected Action Topic
        suffixes.

        :param action_topic: the potential Action TopicBuilder to test
        :type action_topic: TopicBuilder
        :return: True if the TopicBuilder's name suffix falls in the
            expected Action Topic suffixes; False if not
        :rtype: bool
        """
        print(f"CLS = {cls.TOPIC_SUFFIXES}")
        print(
            f"\ttest_potential_action_topic_builder action_topic={action_topic} "
            f"|\x1b[91m suffix={action_topic.name_suffix}\x1b[0m"
        )

        print(
            f"ACTION_TOPIC: {action_topic.name_suffix}"
            f"\t\t{action_topic.name_suffix in cls.TOPIC_SUFFIXES}"
        )
        return action_topic.name_suffix in cls.TOPIC_SUFFIXES

    @classmethod
    def _validate_topic_builders_have_required_suffixes(cls, topic_builders):
        """
        Verify if the provided TopicBuilders meet the minimum requirements.

        Verify that this is potentially make up this Action;
        this means that at least 3 TopicBuilders were provided and
        have name suffixes that are part of the set of expected
        Action Topic suffixes

        :param topic_builders: the collection of TopicBuilders to check
        :type topic_builders: list[TopicBuilder]
        :return: True if the conditions have been met to consider these
            TopicBuilders as valid to be part of an Action; False if
            not
        :rtype: bool
        """
        found_topic_suffixes = {
            topic_builder.name_suffix for topic_builder in topic_builders
        }
        return (len(found_topic_suffixes) >= 3) and (
            found_topic_suffixes.issubset(cls.TOPIC_SUFFIXES)
        )

    @classmethod
    def _validate_core_topic_builders_have_required_types(
        cls, topic_name_suffixes_to_builders
    ):
        """
        Verify if the provided TopicBuilders meet more specific requirements.

        Verify requirements to make up this Action; this means that
        the expected Core Topic suffixes that make up any Action must
        be found amongst the provided TopicBuilders and they must all
        have ROS Types that include the expected 'Action<Type>' format

        :param topic_name_suffixes_to_builders: the mapping of Topic
            name suffixes to TopicBuilders to check
        :type topic_name_suffixes_to_builders: dict{str: TopicBuilder}
        :return: True if the conditions have been met to consider these
            TopicBuilders as valid to be part of an Action; False if
            not
        :rtype: bool
        """
        for core_suffix, type_token in cls.CORE_TOPIC_SUFFIXES_TO_TYPE_TOKENS.items():
            if core_suffix not in topic_name_suffixes_to_builders:
                return False
            topic_builder = topic_name_suffixes_to_builders[core_suffix]
            topic_type = getattr(topic_builder, "construct_type", None)
            if not topic_type or not topic_type.endswith(f"Action{type_token}"):
                return False
        return True

    def validate_action_topic_builders(self):
        """
        Verify if the TopicBuilders are valid.

        Verify that make up this Action are,
        in fact, valid and should actually make up this Action

        :return: True if the TopicBuilders are valid; False if not
        :rtype: bool
        """
        valid_topic_suffixes = (
            ActionBuilder._validate_topic_builders_have_required_suffixes(
                list(self.topic_names_to_builders.values())
            )
        )
        valid_core_topic_types = (
            ActionBuilder._validate_core_topic_builders_have_required_types(
                self.topic_name_suffixes_to_builders
            )
        )
        return valid_topic_suffixes and valid_core_topic_types

    def _extract_suffix_names_to_topic_metamodels(self):
        """
        Extract and return a mapping of Action Topics.

        Extract name suffixes to Topic models from the TopicBuilders that
        make up this Action

        :return: the mapping of Action Topic name suffixes to extracted
            Topics
        :rtype: dict{str: Topic}
        """
        print(f"\n\n\nACTION_BUILDER SUFFIX LIST: {ActionBuilder.TOPIC_SUFFIXES}")
        print(f"TOPIC_NAME_SUFFIXES: {self.topic_name_suffixes_to_builders}")
        return {key: "not_completed" for key in ActionBuilder.TOPIC_SUFFIXES}

    def extract_metamodel(self):
        """
        Extract metamodel.

        Allows the ActionBuilder to create / extract an Action
        instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: Action
        """
        action_metamodel = Action(
            source="ros_snapshot",
            name=self.name,
            construct_type=self.construct_type,
            client_node_names=self.client_node_names,
            server_node_names=self.server_node_names,
        )
        return action_metamodel
