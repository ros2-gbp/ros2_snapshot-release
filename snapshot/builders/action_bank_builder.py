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
Module for *BankBuilders.

BankBuilders are responsible for collecting, maintaining,
and populating *EntityBuilders for the purpose of extracting metamodel
instances
"""

from core.metamodels import ActionBank

from snapshot.builders.action_builder import ActionBuilder
from snapshot.builders.base_builders import _BankBuilder


class ActionBankBuilder(_BankBuilder):
    """
    Define an ActionBankBuilder.

    ActionBankBuilder is responsible for collecting,
    maintaining, and populating ActionBuilders for the purpose of
    extracting metamodel instances
    """

    def _create_entity_builder(self, name):
        """
        Create and return a new ActionBuilder instance.

        :param name: the name used to instantiate the new ActionBuilder
        :type name: str
        :return: the newly created ActionBuilder
        :rtype: ActionBuilder
        """
        return ActionBuilder(name)

    def _create_bank_metamodel(self):
        """
        Create and return a new ActionBank instance.

        :return: a newly created ActionBank instance
        :rtype: ActionBank
        """
        return ActionBank()
