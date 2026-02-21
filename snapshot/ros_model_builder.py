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

"""Module for the ROSModelBuilder."""

from core.ros_model import BankType, ROSModel

from snapshot.builders import (
    ActionBankBuilder,
    MachineBankBuilder,
    NodeBankBuilder,
)
from snapshot.builders import (
    ParameterBankBuilder,
    ServiceBankBuilder,
    TopicBankBuilder,
)


class ROSModelBuilder:
    """
    Class responsible for creating and preparing BankBuilders.

    Allows extraction of a fully populated ROSModel.
    """

    def __init__(self, topic_types):
        """
        Instantiate an instance of the ROSModelBuilder.

        :param topic_types: the collection or iterable of topic name,
            topic type pairs
        :type topic_types: list[tuple(str, str)]
        """
        self._bank_builders = {
            BankType.NODE: NodeBankBuilder(),
            BankType.TOPIC: TopicBankBuilder(topic_types),
            BankType.ACTION: ActionBankBuilder(),
            BankType.SERVICE: ServiceBankBuilder(),
            BankType.PARAMETER: ParameterBankBuilder(),
            BankType.MACHINE: MachineBankBuilder(),
        }

    def get_bank_builder(self, bank_builder_type):
        """
        Return a desired BankBuilder.

        :param bank_builder_type: the key to retrieve the BankBuilder by
        :type bank_builder_type: BankType
        :return: the desired BankBuilder
        :rtype: BankBuilder
        """
        return self._bank_builders[bank_builder_type]

    def prepare(self):
        """Prepare the individual BankBuilders to help build the ROSModel."""
        topic_bank_builder = self.get_bank_builder(BankType.TOPIC)
        action_bank_builder = self.get_bank_builder(BankType.ACTION)

        for bank_builder_type in ROSModel.DEPLOYMENT_TYPES:
            if (
                bank_builder_type != BankType.NODE
                and bank_builder_type != BankType.MACHINE
            ):
                self.get_bank_builder(bank_builder_type).prepare()

        self.get_bank_builder(BankType.NODE).prepare(
            topic_bank_builder=topic_bank_builder,
            action_bank_builder=action_bank_builder,
        )
        self.get_bank_builder(BankType.MACHINE).prepare(
            node_builders=self.get_bank_builder(BankType.NODE)
        )

    def _extract_metamodels(self):
        """
        Extract the individual metamodels from each of the BankBuilders.

        :return: a dictionary of bank names to *Bank instances
        :rtype: dict{str: *Bank}
        """
        bank_builder_types_to_metamodels = {}
        for bank_builder_type, instance in list(self._bank_builders.items()):
            if bank_builder_type == BankType.NODE:
                bank_builder_types_to_metamodels[BankType.NODE] = (
                    instance.extract_node_bank_metamodel()
                )
            else:
                bank_builder_types_to_metamodels[bank_builder_type] = (
                    instance.extract_metamodel()
                )

        return bank_builder_types_to_metamodels

    def extract_model(self):
        """
        Extract the ROSModel instance.

        :return: the extracted, populated ROSModel
        :rtype: ROSModel
        """
        return ROSModel(self._extract_metamodels())
