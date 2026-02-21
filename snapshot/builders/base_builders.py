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
Module for base EntityBuilder and BankBuilder Classes.

These define the basic operations used to extract metamodels in the
snapshot_modeling format.
"""

from abc import ABCMeta, abstractmethod


class _EntityBuilder(object, metaclass=ABCMeta):
    """
    Abstract Base Class for *EntityBuilders.

    EntityBuilders represent ROS
    Entities and are responsible for allowing themselves to be
    populated with basic information and then further populating
    themselves from that information for the purpose of extracting
    metamodel instances
    """

    def __init__(self, name):
        """
        Instantiate an instance of the _EntityBuilder base class.

        :param name: the name of the ROS Entity to represent
        :type name: str
        """
        self._name = name
        name_tokens = name.split("/")
        self._name_suffix = f"/{name_tokens[-1]}"
        self._name_base = "/".join(
            name_tokens[0 : (len(name_tokens) - 1)]  # noqa: E203
        )

    def prepare(self, **kwargs):
        """
        Allow a subclass, if applicable, to prepare its internal state.

        Used for eventual metamodel extraction; internal changes to the state
        of the class instance occur here, if applicable

        :param kwargs: keyword arguments used in the preparation process
        :type kwargs: dict{param: value}
        """
        return

    @property
    def name(self):
        """
        Return the name of the ROS Entity.

        :return: the name of the ROS Entity
        :rtype: str
        """
        return self._name

    @property
    def name_suffix(self):
        """
        Return the last token of the ROS Entity name.

        Tokens are
        created by splitting the name on forward slashes

        :return: the last token of the ROS Entity name
        :rtype: str
        """
        return self._name_suffix

    @property
    def name_base(self):
        """
        Return the first token of the ROS Entity name.

        Tokens are
        created by splitting the name on forward slashes

        :return: the first token of the ROS Entity name
        :rtype: str
        """
        return self._name_base

    @abstractmethod
    def extract_metamodel(self):
        """
        Extract metamodel.

        Abstract method that allows a subclass to implement its unique
        *EntityMetamodel creation and population functionality to
        create / extract a metamodel instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: *EntityMetamodel
        """
        return


class _BankBuilder(object, metaclass=ABCMeta):
    """
    Abstract base class for *BankBuilders.

    BankBuilders are responsible for
    collecting, maintaining, and populating *EntityBuilders for the
    purpose of extracting metamodel instances
    """

    def __init__(self):
        """Instantiate an instance of the _BankBuilder base class."""
        self._names_to_entity_builders = {}

    def __getitem__(self, name):
        """
        Return the appropriate *EntityBuilder from the bank.

        Instantiates a new builder if one is not already present for
        the name

        :param name: the key to identify the desired *EntityBuilder
        :type name: str
        :return: the matching *EntityBuilder, either newly added or
            retrieved
        :rtype: *EntityBuilder
        """
        if name not in self.names_to_entity_builders:
            entity_builder = self._create_entity_builder(name)
            self.add_entity_builder(entity_builder)
        return self.names_to_entity_builders[name]

    @property
    def items(self):
        """Get list of key, builder pairs."""
        return list(self.names_to_entity_builders.items())

    @property
    def names_to_entity_builders(self):
        """
        Return the dictionary of entity names to *EntityBuilders.

        :return: the dictionary of entity names to *EntityBuilders
        :rtype: dict{str: *EntityBuilder}
        """
        return self._names_to_entity_builders

    def add_entity_builder(self, entity_builder):
        """
        Add an *EntityBuilder to the internal store of builders.

        :param entity_builder: the *EntityBuilder to add
        :type entity_builder: *EntityBuilder
        """
        self._names_to_entity_builders[entity_builder.name] = entity_builder

    def add_entity_builders(self, entity_builders):
        """
        Add an iterable collection of *EntityBuilders.

        Added to the internal store of builders.

        :param entity_builders: an iterable collection of
            *EntityBuilders to add
        :type entity_builders: list[*EntityBuilder]
        """
        for entity_builder in entity_builders:
            self.add_entity_builder(entity_builder)

    def remove_entity_builder(self, name):
        """
        Remove an *EntityBuilder from the internal store of builders.

        Removes one that corresponds to a given name key

        :param name: the key to identify the desired *EntityBuilder to
            remove
        :type name: str
        """
        self._names_to_entity_builders.pop(name)

    @abstractmethod
    def _create_entity_builder(self, name):
        """
        Create entity builder.

        Abstract method that allows subclasses to create and return a
        new *EntityBuilder

        :param name: the name used to instantiate the new *EntityBuilder
        :type name: str
        :return: the newly created *EntityBuilder
        :rtype: *EntityBuilder
        """
        return

    def _gather_filtered_names_to_entity_builders(self):
        """
        Gather and return a dictionary of names.

        Names are filtered
        *EntityBuilders; the filter is based on the class's
        implementation of its filtering method

        :return: a dictionary of names to filtered *EntityBuilders
        :rtype: dict{str: *EntityBuilder}
        """
        filtered_names_to_entity_builders = {}
        for name, entity_builder in list(self.names_to_entity_builders.items()):
            if not self._should_filter_out(name, entity_builder):
                filtered_names_to_entity_builders[name] = entity_builder
        return filtered_names_to_entity_builders

    def _should_filter_out(self, name, entity_builder):
        """
        Indicate whether a given *EntityBuilder should be filtered.

        Use name to
        identify whether it should be filtered out or not; unless implemented
        by a subclass, this method always returns False

        :param name: the name to identify the *EntityBuilder
        :type name: str
        :param entity_builder: the *EntityBuilder to check
        :type entity_builder: *EntityBuilder
        :return: True if the *EntityBuilder should be filtered out;
            False if not
        :rtype: bool
        """
        return False

    def prepare(self, **kwargs):
        """
        Prepare the internal *EntityBuilders for eventual metamodel extraction.

        Internal changes to the state of the *EntityBuilders
        occur for the builders that are stored in the internal bank

        :param kwargs: keyword arguments needed by the underlying
            *EntityBuilders used in the preparation process
        :type kwargs: dict{param: value}
        """
        self._names_to_entity_builders = (
            self._gather_filtered_names_to_entity_builders()
        )
        for name in self.names_to_entity_builders:
            self.names_to_entity_builders[name].prepare(**kwargs)
        self._post_prepare()

    def _post_prepare(self):
        """
        Allow an implementing subclass to either wrap up.

        Or to begin a new set of tasking necessary for eventual metamodel population
        """
        return

    @abstractmethod
    def _create_bank_metamodel(self):
        """
        Create and return their appropriate *BankMetamodel.

        :return: the appropriate, newly created *BankMetamodel instance
        :rtype: *BankMetamodel
        """
        return

    @property
    def _names_to_entity_builder_metamodels(self):
        """
        Return a dictionary of names to extracted.

        *Metamodel instances from each of their respective
        *EntityBuilder instances in the internal store of
        *EntityBuilders

        :return: a dictionary of names to extracted *Metamodel instances
        :rtype: dict{str: *Metamodel}
        """
        return {
            name: entity_builder.extract_metamodel()
            for (name, entity_builder) in list(self.names_to_entity_builders.items())
        }

    def extract_metamodel(self):
        """
        Extract and return an instance of the *BankMetamodel.

        :return: an extracted instance of this builder's *BankMetamodel
        :rtype: *BankMetamodel
        """
        bank_metamodel = self._create_bank_metamodel()
        bank_metamodel.names_to_metamodels = self._names_to_entity_builder_metamodels
        return bank_metamodel
