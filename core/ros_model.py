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

"""A model of ROS system deployment as banks of metamodel instances."""

import json
import os
import pickle
import sys
import traceback
from enum import Enum, unique
from subprocess import CalledProcessError
from typing import Any, Type

import core.metamodels
from core.base_metamodel import _BankMetamodel, _EntityMetamodel
from core.utilities.logger import Logger, LoggerLevel
from core.utilities.utility import (
    create_directory_path,
    get_input_file_type,
)

from graphviz import Digraph
from graphviz import RequiredArgumentError
from graphviz.backend import ExecutableNotFound

import yaml


@unique
class BankType(Enum):
    """Enumerated type for Bank identifiers."""

    NODE = 1
    TOPIC = 2
    ACTION = 3
    SERVICE = 4
    PARAMETER = 5
    MACHINE = 6
    PACKAGE_SPECIFICATION = 7
    NODE_SPECIFICATION = 8
    MESSAGE_SPECIFICATION = 9
    SERVICE_SPECIFICATION = 10
    ACTION_SPECIFICATION = 11


class ROSModel:
    """The ROS Model class definition."""

    SPECIFICATION_TYPES = [
        BankType.PACKAGE_SPECIFICATION,
        BankType.NODE_SPECIFICATION,
        BankType.MESSAGE_SPECIFICATION,
        BankType.SERVICE_SPECIFICATION,
        BankType.ACTION_SPECIFICATION,
    ]

    DEPLOYMENT_TYPES = []

    BANK_TYPES_TO_OUTPUT_NAMES = {
        BankType.NODE: "node_bank",
        BankType.TOPIC: "topic_bank",
        BankType.ACTION: "action_bank",
        BankType.SERVICE: "service_bank",
        BankType.PARAMETER: "parameter_bank",
        BankType.MACHINE: "machine_bank",
        BankType.PACKAGE_SPECIFICATION: "package_specification_bank",
        BankType.NODE_SPECIFICATION: "node_specification_bank",
        BankType.MESSAGE_SPECIFICATION: "message_specification_bank",
        BankType.SERVICE_SPECIFICATION: "service_specification_bank",
        BankType.ACTION_SPECIFICATION: "action_specification_bank",
    }

    BANK_TYPES_TO_BANK_CLASS = {
        BankType.NODE: core.metamodels.NodeBank,
        BankType.TOPIC: core.metamodels.TopicBank,
        BankType.ACTION: core.metamodels.ActionBank,
        BankType.SERVICE: core.metamodels.ServiceBank,
        BankType.PARAMETER: core.metamodels.ParameterBank,
        BankType.MACHINE: core.metamodels.MachineBank,
        BankType.PACKAGE_SPECIFICATION: core.metamodels.PackageSpecificationBank,
        BankType.NODE_SPECIFICATION: core.metamodels.NodeSpecificationBank,
        BankType.MESSAGE_SPECIFICATION: core.metamodels.TypeSpecification,
        BankType.SERVICE_SPECIFICATION: core.metamodels.TypeSpecification,
        BankType.ACTION_SPECIFICATION: core.metamodels.TypeSpecification,
    }

    _ros_model_yaml_initialized = False

    def __init__(self, bank_dictionary):
        """Initialize instance and classify entity types by spec or deployment."""
        if len(ROSModel.DEPLOYMENT_TYPES) == 0:
            ROSModel.DEPLOYMENT_TYPES.extend(
                [bt for bt in BankType if bt not in ROSModel.SPECIFICATION_TYPES]
            )

        self._bank_dictionary = bank_dictionary

    @property
    def keys(self):
        """Return keys to model bank dictionary."""
        return list(self._bank_dictionary.keys())

    @property
    def items(self):
        """Return key, value list of model bank dictionary."""
        return list(self._bank_dictionary.items())

    def update_bank(self, bank_type, bank_dictionary):
        """
        Add a new bank data to ROS model.

        :param bank_type: a BankType
        :param bank_dictionary: dictionary of name to entity instances
        """
        if bank_type not in BankType:
            raise ValueError(f"Invalid bank type '{bank_type}'")

        if bank_type not in self._bank_dictionary:
            self._bank_dictionary[bank_type] = {}

        # Validate the inputs
        for key, value in list(bank_dictionary.items()):
            if not isinstance(key, str):
                raise KeyError(
                    f"ROSModel.update_bank: All keys must be strings - not '{type(key)}'"
                )
            if not isinstance(value, self._bank_dictionary[bank_type].entity_class):
                raise ValueError(
                    "ROSModel.update_bank: All values must be "
                    f"'{self._bank_dictionary[bank_type].entity_class.__name__}'"
                    f" - not '{value.__class__.__name__}'"
                )

        # Merge dictionaries
        Logger.get_logger().log(
            LoggerLevel.INFO, f"Update '{self.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]}'"
        )
        self._bank_dictionary[bank_type].update(bank_dictionary)

    def __getitem__(self, key):
        """
        Get specific instance from key.

        :return: bank of metamodel instances from key
        """
        if key not in self._bank_dictionary:
            raise KeyError(f"Invalid key to bank dictionary '{key}'")
        return self._bank_dictionary[key]

    @property
    def node_bank(self):
        """Return node bank."""
        return self._bank_dictionary[BankType.NODE]

    @property
    def topic_bank(self):
        """Return topic bank."""
        return self._bank_dictionary[BankType.TOPIC]

    @property
    def action_bank(self):
        """Return action bank."""
        return self._bank_dictionary[BankType.ACTION]

    @property
    def service_bank(self):
        """Return service bank."""
        return self._bank_dictionary[BankType.SERVICE]

    @property
    def parameter_bank(self):
        """Return parameter bank."""
        return self._bank_dictionary[BankType.PARAMETER]

    @property
    def machine_bank(self):
        """Return machine bank."""
        return self._bank_dictionary[BankType.MACHINE]

    @property
    def message_specification_bank(self):
        """Return message specification bank."""
        return self._bank_dictionary[BankType.MESSAGE_SPECIFICATION]

    @property
    def service_specification_bank(self):
        """Return service specification bank."""
        return self._bank_dictionary[BankType.SERVICE_SPECIFICATION]

    @property
    def action_specification_bank(self):
        """Return action specification bank."""
        return self._bank_dictionary[BankType.ACTION_SPECIFICATION]

    @property
    def package_specification_bank(self):
        """Return package specification bank."""
        return self._bank_dictionary[BankType.PACKAGE_SPECIFICATION]

    @property
    def node_specification_bank(self):
        """Return node specification bank."""
        return self._bank_dictionary[BankType.NODE_SPECIFICATION]

    def save_model_info_files(self, directory_path, base_file_name):
        """
        Save the ROS model to human-readable files.

        :param directory_path : directory to store files
        :param base_file_name: file name string
        :return:
        """
        try:
            directory_path = create_directory_path(directory_path)
            for bank_type, bank in list(self._bank_dictionary.items()):

                rows = []
                rows.append(str(bank))
                bank_output_name = ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]

                file_path = os.path.join(
                    directory_path, f"{base_file_name}_{bank_output_name}.txt"
                )
                with open(file_path, "w") as fout:
                    fout.write("\n".join(rows))

        except IOError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to save human-readable files for ROS Computation Graph.",
            )
            print("     ", ex)

    def save_model_json_files(self, directory_path, base_file_name):
        """
        Save the ROS bank metamodel instances to json files (preferred by Pydantic).

        :param directory_path : directory to store files
        :param base_file_name:
        :return: None
        """
        try:

            def metamodel_json_encoder(obj):
                if isinstance(obj, _EntityMetamodel):
                    obj_dict = obj.dict()
                    obj_dict["__type__"] = obj.__class__.__name__
                    return obj_dict
                elif isinstance(obj, _BankMetamodel):
                    return {
                        "__type__": obj.__class__.__name__,
                        "names_to_metamodels": {
                            k: metamodel_json_encoder(v) for k, v in obj.items
                        },
                    }
                raise TypeError(
                    f"Object of type {obj.__class__.__name__} is not JSON serializable"
                )

            directory_path = create_directory_path(directory_path)
            for bank_type, bank in list(self._bank_dictionary.items()):

                bank_output_name = ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]
                file_path = os.path.join(
                    directory_path, f"{base_file_name}_{bank_output_name}.json"
                )
                json_output = json.dumps(
                    bank, default=metamodel_json_encoder, indent=2, sort_keys=True
                )
                with open(file_path, "w") as fout:
                    fout.write(json_output)
        except IOError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to save YAML files for ROS Computation Graph.",
            )
            print("     ", ex)

    def save_model_yaml_files(self, directory_path, base_file_name):
        """
        Save the ROS bank metamodel instances to yaml files.

        :param directory_path : directory to store files
        :param base_file_name:
        :return: None
        """
        if not ROSModel._ros_model_yaml_initialized:
            ROSModel.get_yaml_processors()

        try:
            directory_path = create_directory_path(directory_path)

            for bank_type, bank in list(self._bank_dictionary.items()):

                bank_output_name = ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]
                file_path = os.path.join(
                    directory_path, f"{base_file_name}_{bank_output_name}.yaml"
                )
                with open(file_path, "w") as fout:
                    yaml.dump(bank, fout, sort_keys=True)
        except IOError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to save YAML files for ROS Computation Graph.",
            )
            print("     ", ex)

    def save_model_pickle_files(self, directory_path, base_file_name):
        """
        Save the ROS bank metamodel instances to Pickle files.

        :param directory_path : directory to store files
        :param base_file_name:
        :return: None
        """
        try:
            directory_path = create_directory_path(directory_path)
            for bank_type, bank in list(self._bank_dictionary.items()):
                bank_output_name = ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]
                file_path = os.path.join(
                    directory_path, f"{base_file_name}_{bank_output_name}.pkl"
                )
                with open(file_path, "wb") as fout:
                    pickle.dump(bank, fout)
        except IOError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR, "Failed to save Pickle files for ROS Model."
            )
            print("     ", ex)

    def save_dot_graph_files(self, directory_path, file_name, show_graph=True):
        """
        Save the ROS model computation graph to DOT file format.

        :param directory_path : directory to store files
        :param file_name: file name of the graph data
        :param show_graph: show output when complete
        :return: None
        """
        try:
            Logger.get_logger().log(
                LoggerLevel.INFO,
                f"Saving DOT files for ROS Model to '{directory_path}' ...",
            )
            directory_path = create_directory_path(directory_path)
            dot_graph = Digraph(
                comment="ROS Computation Graph",
                engine="dot",
                graph_attr={"concentrate": "true"},
                directory=directory_path,
            )
            for bank in list(self._bank_dictionary.values()):
                bank.add_to_dot_graph(dot_graph)

            Logger.get_logger().log(
                LoggerLevel.INFO,
                f"Render ROS Computation Graph. (show_graph='{show_graph}')",
            )
            dot_graph.render(f"{file_name}.dot", view=show_graph, quiet=False)

        except IOError:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to write DOT files for ROS Computation Graph.\n"
                f"    IOError for {directory_path}/{file_name}",
            )

        except ExecutableNotFound:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to write DOT files for ROS Computation Graph.\n"
                "             The Graphviz executable is not found.",
            )

        except CalledProcessError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to write DOT files for ROS Computation Graph.\n"
                "             The Graphviz render exit status is non-zero",
            )
            print("     ", ex)

        except RequiredArgumentError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to write DOT files for ROS Computation Graph.\n"
                "              renderer is none!",
            )
            raise ex

        except ValueError as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                "Failed to write DOT files for ROS Computation Graph.\n"
                "             Render engine, format, renderer, or formatter are not known.",
            )
            raise ex

    @staticmethod
    def get_yaml_processors():
        """Return YAML handler."""
        Logger.get_logger().log(
            LoggerLevel.DEBUG, " Set up YAML processing for meta models ..."
        )

        def entity_representer(dumper, data):
            """Define custom YAML representers to simplify the Pydantic output."""
            node = dumper.represent_dict(data.dict(exclude_unset=True))
            node.tag = data.yaml_tag
            return node

        def bank_representer(dumper, data):
            # Specifying this way is required to call entities properly
            node = dumper.represent_dict(
                {"names_to_metamodels": data.names_to_metamodels}
            )
            node.tag = data.yaml_tag
            return node

        def entity_constructor(loader, node, model_class: Type[_EntityMetamodel]):
            try:
                values = loader.construct_mapping(node, deep=True)
                return model_class(**values)
            except Exception as exc:  # noqa: B902
                raise exc

        def bank_constructor(loader, node, bank_class: Type[_BankMetamodel]):
            try:
                values = loader.construct_mapping(node, deep=True)
                names_to_metamodels = dict(values["names_to_metamodels"].items())
                return bank_class(names_to_metamodels=names_to_metamodels)
            except Exception as exc:  # noqa: B902

                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    (
                        f"Invalid bank constructor {node.id} {node.tag} {bank_class.__name__} - {type(exc)}\n"
                        f"Invalid bank construction {type(exc)} - {exc}\n"
                        f"{traceback.format_exc()}"
                    ),
                )
                sys.exit(-1)

        # Register representers for all metaclasses dynamically
        for subclass in _EntityMetamodel.__subclasses__():
            yaml.add_representer(subclass, entity_representer)
            # The lambda functions used for the constructors have a default argument (subclass=subclass).
            # This ensures that the lambda function captures the current value of subclass when it is defined,
            # rather than the last value of the loop variable.
            yaml.add_constructor(
                subclass.yaml_tag,
                lambda loader, node, subclass=subclass: entity_constructor(
                    loader, node, subclass
                ),
            )
        for subclass in _BankMetamodel.__subclasses__():
            yaml.add_representer(subclass, bank_representer)
            yaml.add_constructor(
                subclass.yaml_tag,
                lambda loader, node, subclass=subclass: bank_constructor(
                    loader, node, subclass
                ),
            )

        ROSModel._ros_model_yaml_initialized = True

    @staticmethod
    def read_model_from_yaml(directory_path, base_file_name, spec_only=False):
        """
        Read model banks from directory containing YAML files.

        :param directory_path: file path to YAML files
        :param base_file_name: base file name used in YAML files
        :return : instance of ROSModel
        """
        if not ROSModel._ros_model_yaml_initialized:
            ROSModel.get_yaml_processors()

        bank_dict = {}
        Logger.get_logger().log(
            LoggerLevel.DEBUG, "Reading ROS model from yaml files ..."
        )
        for bank_type, bank_output_name in ROSModel.BANK_TYPES_TO_OUTPUT_NAMES.items():
            if spec_only and bank_type not in ROSModel.SPECIFICATION_TYPES:
                continue

            file_path = os.path.join(
                os.path.expanduser(directory_path),
                f"{base_file_name}_{bank_output_name}.yaml",
            )
            try:
                with open(file_path, "r") as fin:
                    bank_data = yaml.load(fin, Loader=yaml.FullLoader)
                    if "specification" not in file_path:
                        print(f"DATA: \t{bank_data}")
                    bank_dict[bank_type] = bank_data
            except yaml.constructor.ConstructorError as exc:
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Failed to read YAML data for '{bank_output_name}' : '{file_path}'\n"
                    f"     {type(exc)} - {exc}",
                )

                bank_dict[bank_type] = ROSModel.BANK_TYPES_TO_BANK_CLASS[bank_type]()
            except IOError:
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Failed to read YAML data for '{bank_output_name}' : '{file_path}'",
                )
                bank_dict[bank_type] = ROSModel.BANK_TYPES_TO_BANK_CLASS[bank_type]()

        # Create instance of the model class
        return ROSModel(bank_dict)

    @staticmethod
    def read_model_from_json(directory_path, base_file_name, spec_only=False):
        """
        Read model banks from directory containing JSON files.

        :param directory_path: file path to JSON files
        :param base_file_name: base file name used in JSON files
        :return : instance of ROSModel
        """
        bank_dict = {}
        Logger.get_logger().log(
            LoggerLevel.DEBUG, "Reading ROS model from JSON files ..."
        )

        def _deserialize_json(data: dict) -> Any:
            """Deserialize json into one of our model banks."""
            type_name = data.pop("__type__")
            if not type_name:
                raise ValueError("No __type__ field found in JSON data")

            bank_class = _BankMetamodel.get_model_class_from_type(type_name)
            if bank_class is None:
                model_class = _EntityMetamodel.get_model_class_from_type(type_name)
                if not model_class:
                    raise ValueError(f"No class found for type '{type_name}'")
                return model_class(**data)
            else:
                data["names_to_metamodels"] = {
                    k: _deserialize_json(v)
                    for k, v in data["names_to_metamodels"].items()
                }
                return bank_class(**data)

        for bank_type, bank_output_name in ROSModel.BANK_TYPES_TO_OUTPUT_NAMES.items():
            if spec_only and bank_type not in ROSModel.SPECIFICATION_TYPES:
                continue

            file_path = os.path.join(
                os.path.expanduser(directory_path),
                f"{base_file_name}_{bank_output_name}.json",
            )
            try:
                with open(file_path, "r") as fin:
                    json_data = fin.read()
                    bank_dict[bank_type] = _deserialize_json(json.loads(json_data))
            except IOError:
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Failed to read JSON data for '{bank_output_name}' : '{file_path}",
                )
                bank_dict[bank_type] = ROSModel.BANK_TYPES_TO_BANK_CLASS[bank_type]()

        # Create instance of the model class
        return ROSModel(bank_dict)

    @staticmethod
    def read_model_from_pickle(directory_path, base_file_name, spec_only=False):
        """
        Read model banks from directory containing Pickle files.

        :param directory_path: file path to Pickle files
        :param base_file_name: base file name used in Pickle files
        :return : instance of ROSModel
        """
        bank_dict = {}
        Logger.get_logger().log(
            LoggerLevel.DEBUG, "Reading ROS model from pickle files ..."
        )
        for bank_type, bank_output_name in ROSModel.BANK_TYPES_TO_OUTPUT_NAMES.items():
            if spec_only and bank_type not in ROSModel.SPECIFICATION_TYPES:
                continue

            file_path = os.path.join(
                os.path.expanduser(directory_path),
                f"{base_file_name}_{bank_output_name}.pkl",
            )

            class SafeUnpickler(pickle.Unpickler):
                """Define unpickle that will only process our metadata files or builtin."""

                def find_class(self, module, name):
                    # Only allow some safe classes to be unpickled
                    if module == "builtins" and name in {
                        "set",
                        "frozenset",
                        "tuple",
                        "list",
                        "dict",
                        "str",
                        "int",
                        "float",
                        "bool",
                    }:
                        return getattr(__import__(module), name)
                    meta_class = _BankMetamodel.get_model_class_from_type(
                        name
                    ) or _EntityMetamodel.get_model_class_from_type(name)
                    if meta_class is not None:
                        return meta_class
                    # Otherwise, raise an error
                    raise pickle.UnpicklingError(
                        f"Attempting to unpickle unsafe class: '{module}.{name}'"
                    )

            try:
                with open(file_path, "rb") as fin:
                    bank_dict[bank_type] = SafeUnpickler(fin).load()
            except (IOError, pickle.UnpicklingError) as exc:
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Failed to read Pickle data for '{bank_output_name}' : '{file_path}' with {type(exc)}",
                )
                bank_dict[bank_type] = ROSModel.BANK_TYPES_TO_BANK_CLASS[bank_type]()
            except Exception as exc:  # noqa: B902
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Unexpected Error: Failed to read Pickle data for '{bank_output_name}' : '{file_path}' with {type(exc)}",
                )

                print(traceback.format_exc(), flush=True)

                sys.exit(-1)
                bank_dict[bank_type] = ROSModel.BANK_TYPES_TO_BANK_CLASS[bank_type]()

        # Create instance of the model class
        return ROSModel(bank_dict)

    @staticmethod
    def load_model(input_directory, spec_only=False):
        """
        Load  model from folder.

        :param input_directory: the input directory pointing to either yaml, json, or pickle files (e.g. output/yaml)
        :return: ROSModel instance with models stored in dictionary by type
        """
        try:
            input_type, input_base_file_name = get_input_file_type(input_directory)
        except IOError:
            return None

        if input_type == "yaml":
            return ROSModel.read_model_from_yaml(
                input_directory, input_base_file_name, spec_only
            )
        elif input_type == "json":
            return ROSModel.read_model_from_json(
                input_directory, input_base_file_name, spec_only
            )
        elif input_type == "pkl":
            return ROSModel.read_model_from_pickle(
                input_directory, input_base_file_name, spec_only
            )
        else:
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                f"Failed to determine input file type for '{input_directory}' ...",
            )
            return None
