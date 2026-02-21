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
Module for NodeBankBuilder.

Responsible for collecting, maintaining,
and populating NodeBuilder instances
"""

from core import metamodels
from core.utilities import filters

from snapshot.builders.base_builders import _BankBuilder
from snapshot.builders.node_builder import NodeBuilder


class NodeBankBuilder(_BankBuilder):
    """
    Define a NodeBankBuilder.

    Responsible for collecting,
    maintaining, and populating NodeBuilders for the purpose of
    extracting metamodel instances
    """

    def get_node_builder(self):
        """Get node builder."""
        return NodeBuilder

    def _create_entity_builder(self, name):
        """
        Create and return a new NodeBuilder instance.

        :param name: the name used to instantiate the new NodeBuilder
        :type name: str
        :return: the newly created NodeBuilder
        :rtype: NodeBuilder
        """
        return NodeBuilder(name)

    def _should_filter_out(self, name, entity_builder):
        """
        Indicate whether the given NodeBuilder should be filtered out or not.

        :param name: the name to identify the NodeBuilder
        :type name: str
        :param entity_builder: the NodeBuilder to check
        :type entity_builder: NodeBuilder
        :return: True if the NodeBuilder should be filtered out;
            False if not
        :rtype: bool
        """
        return filters.NodeFilter.get_filter().should_filter_out(name)

    def _create_bank_metamodel(self):
        """
        Create and return a new NodeBank instance.

        :return: a newly created NodeBank instance
        :rtype: NodeBank
        """
        return metamodels.NodeBank()

    def extract_node_bank_metamodel(self):
        """
        Extract and return an instance of the NodeBank.

        Extracted and populated from this builder (built by this
        builder); only pure Node instances (no subtypes)
        are part of this bank

        :return: an extracted instance of this builder's NodeBank
        :rtype: NodeBank
        """
        bank_metamodel = metamodels.NodeBank()
        all_node_metamodels = self._names_to_entity_builder_metamodels
        bank_metamodel.names_to_metamodels = dict(all_node_metamodels.items())
        return bank_metamodel
