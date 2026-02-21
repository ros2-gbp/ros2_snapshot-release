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
Module for ServiceBankBuilder.

*BankBuilders, which are responsible for collecting, maintaining,
and populating *EntityBuilders for the purpose of extracting metamodel
instances
"""

from core.metamodels import ServiceBank
from core.utilities import filters

from snapshot.builders.base_builders import _BankBuilder
from snapshot.builders.service_builder import ServiceBuilder


class ServiceBankBuilder(_BankBuilder):
    """
    Define a ServiceBankBuilder.

    Responsible for collecting,
    maintaining, and populating ServiceBuilders for the purpose of
    extracting metamodel instances
    """

    def _create_entity_builder(self, name):
        """
        Create and return a new ServiceBuilder instance.

        :param name: the name used to instantiate the new ServiceBuilder
        :type name: str
        :return: the newly created ServiceBuilder
        :rtype: ServiceBuilder
        """
        return ServiceBuilder(name)

    def _should_filter_out(self, name, entity_builder):
        """
        Indicate whether the given ServiceBuilder should be filtered out or not.

        :param name: the name to identify the ServiceBuilder
        :type name: str
        :param entity_builder: the ServiceBuilder to check
        :type entity_builder: ServiceBuilder
        :return: True if the ServiceBuilder should be filtered out;
            False if not
        :rtype: bool
        """
        return filters.ServiceTypeFilter.get_filter().should_filter_out(
            entity_builder.construct_type
        )

    def _create_bank_metamodel(self):
        """
        Create and return a new ServiceBank instance.

        :return: a newly created ServiceBank instance
        :rtype: ServiceBank
        """
        return ServiceBank()
