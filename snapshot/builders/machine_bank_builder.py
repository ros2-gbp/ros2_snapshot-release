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

"""Classes associated with building a bank of machine models."""

from core.metamodels import MachineBank

from snapshot.builders.base_builders import _BankBuilder
from snapshot.builders.machine_builder import MachineBuilder


class MachineBankBuilder(_BankBuilder):
    """
    Define a MachineBankBuilder.

     which is responsible for collecting,
    maintaining, and populating MachineBuilders for the purpose of
    extracting metamodel instances
    """

    def _create_entity_builder(self, name):
        """
        Create and return a new MachineBuilder instance.

        :param name: the name used to instantiate the new MachineBuilder
        :type name: str
        :return: the newly created MachineBuilder
        :rtype: MachineBuilder
        """
        return MachineBuilder(name)

    def _create_bank_metamodel(self):
        """
        Create and return a new MachineBank instance.

        :return: a newly created MachineBank instance
        :rtype: MachineBank
        """
        return MachineBank()

    def prepare(self, **kwargs):
        """
        Prepare the internal MachineBankBuilder based on identified nodes.

        Used for eventual metamodel
        extraction; internal changes to the state of the *EntityBuilders
        occur for the builders that are stored in the internal bank

        :param kwargs: keyword arguments needed by the underlying
            *EntityBuilders used in the preparation process
        :type kwargs: dict{param: value}
        """
        node_builders = kwargs["node_builders"]
        for node_builder in list(node_builders.names_to_entity_builders.values()):
            machine_builder = self.__getitem__(node_builder.machine)
            machine_builder.prepare(node_name=node_builder.name)
