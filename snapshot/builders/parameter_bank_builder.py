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
Module for ParameterBankBuilders.

Responsible for collecting, maintaining,
and populating ParameterBuilder for the purpose of extracting metamodel
instances
"""

from core.metamodels import ParameterBank

from snapshot.builders.base_builders import _BankBuilder
from snapshot.builders.parameter_builder import ParameterBuilder


class ParameterBankBuilder(_BankBuilder):
    """
    Define a ParameterBankBuilder.

    Responsible for collecting,
    maintaining, and populating ParameterBuilders for the purpose of
    extracting metamodel instances
    """

    def _create_entity_builder(self, name):
        """
        Create and return a new ParameterBuilder instance.

        :param name: the name used to instantiate the new ParameterBuilder
        :type name: str
        :return: the newly created ParameterBuilder
        :rtype: ParameterBuilder
        """
        return ParameterBuilder(name)

    def _create_bank_metamodel(self):
        """
        Create and return a new ParameterBank instance.

        :return: a newly created ParameterBank instance
        :rtype: ParameterBank
        """
        return ParameterBank()
