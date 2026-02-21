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
Module for TopicBankBuilders.

Responsible for collecting, maintaining,
and populating TopicBuilders for the purpose of extracting metamodel
instances
"""

from core.metamodels import TopicBank
from core.utilities import filters

from snapshot.builders.base_builders import _BankBuilder
from snapshot.builders.topic_builder import TopicBuilder


class TopicBankBuilder(_BankBuilder):
    """
    Define a TopicBankBuilder.

    Responsible for collecting,
    maintaining, and populating TopicBuilders for the purpose of
    extracting metamodel instances
    """

    def __init__(self, topic_types):
        """
        Instantiate an instance of the TopicBankBuilder class.

        :param topic_types: the collection or iterable of topic name,
            topic type pairs
        :type topic_types: list[tuple(str, str or list(str))]
        """
        super(TopicBankBuilder, self).__init__()
        self._topic_types = topic_types

    def _create_entity_builder(self, name):
        """
        Create and return a new TopicBuilder instance.

        :param name: the name used to instantiate the new TopicBuilder
        :type name: str
        :return: the newly created TopicBuilder
        :rtype: TopicBuilder
        """
        topic_builder = TopicBuilder(name)
        topic_builder.construct_type = self._find_topic_type(topic_builder.name)
        return topic_builder

    def _should_filter_out(self, name, entity_builder):
        """
        Indicate if should filter out.

        Indicates whether the given TopicBuilder (which has a name to
        identify it) should be filtered out or not

        :param name: the name to identify the TopicBuilder
        :type name: str
        :param entity_builder: the TopicBuilder to check
        :type entity_builder: TopicBuilder
        :return: True if the TopicBuilder should be filtered out;
            False if not
        :rtype: bool
        """
        return filters.TopicFilter.get_filter().should_filter_out(name)

    def _find_topic_type(self, desired_topic):
        """
        Find topic type.

        Helper method that returns the topic type associated with a
        desired topic

        :param desired_topic: the name of the desired topic
        :type desired_topic: str
        :return: the name of the desired topic's type
        :rtype: str
        """
        for topic, topic_type in self._topic_types:
            if topic == desired_topic:
                obtained_topic_type = topic_type
                if isinstance(obtained_topic_type, (list, tuple)):
                    if len(obtained_topic_type) > 1:
                        print(
                            f"\x1b[93m Warning: Topic '{desired_topic}' has multiple types!\n{obtained_topic_type}]",
                            flush=True,
                        )
                    else:
                        obtained_topic_type = obtained_topic_type[0]
                return obtained_topic_type

        return "Error: Unknown Topic Name"

    def _create_bank_metamodel(self):
        """
        Create and return a new TopicBank instance.

        :return: a newly created TopicBank instance
        :rtype: TopicBank
        """
        return TopicBank()

    def _remove_action_topic_builders(self, action_topic_builders):
        """
        Remove action topic from topic builder.

        Remove TopicBuilders from the internal store if they are a
        part of the provided ActionBuilders

        :param action_topic_builders: a collection of ActionBuilders
        :type action_topic_builders: list[ActionBuilder]
        """
        for action_topic_builder in action_topic_builders:
            self.names_to_entity_builders.pop(action_topic_builder.name)
