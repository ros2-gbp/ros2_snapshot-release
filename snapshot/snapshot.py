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
Snapshot: a tool for probing active ROS deployments.

Discovers the ROS Computation Graph and stores as a snapshot_modeling model
"""

import argparse
import os
import socket
import subprocess
import sys
import threading
import time
import traceback

from ament_index_python.packages import get_package_share_directory

from core.ros_model import BankType, ROSModel
from core.utilities import filters
from core.utilities.logger import Logger, LoggerLevel

from pydantic.error_wrappers import ValidationError

from ros2cli.node.strategy import NodeStrategy

from ros2component.api import find_container_node_names
from ros2component.api import get_components_in_container

from ros2node.api import get_action_client_info
from ros2node.api import get_action_server_info
from ros2node.api import get_node_names
from ros2node.api import get_publisher_info
from ros2node.api import get_service_server_info
from ros2node.api import get_subscriber_info

from ros2param.api import call_describe_parameters
from ros2param.api import call_get_parameters
from ros2param.api import call_list_parameters
from ros2param.api import get_value

from snapshot.builders.node_builder import NodeBuilder
from snapshot.remapper_bank import RemapperBank
from snapshot.ros_model_builder import ROSModelBuilder


class ROSSnapshot:
    """
    Class responsible for discovering the main components.

    Discovers the main components in the ROS Computation Graph,
    which are needed to extract a ROSModel.
    """

    def __init__(self, name="/ros_snapshot"):
        """Instantiate an instance of the ROSSnapshot."""
        self._name = name
        self._ros_model_builder = None
        self._ros_deployment_model = None
        self._ros_specification_model = None
        self.specification_update = False
        self._unmatched_nodes = []

    @property
    def node_bank(self):
        """
        Return the NodeBankBuilder.

        :return: the NodeBankBuilder
        :rtype: NodeBankBuilder
        """
        return self._ros_model_builder.get_bank_builder(BankType.NODE)

    @property
    def topic_bank(self):
        """
        Return the TopicBankBuilder.

        :return: the TopicBankBuilder
        :rtype: TopicBankBuilder
        """
        return self._ros_model_builder.get_bank_builder(BankType.TOPIC)

    @property
    def action_bank(self):
        """
        Return the ActionBankBuilder.

        :return: the ActionBankBuilder
        :rtype: ActionBankBuilder
        """
        return self._ros_model_builder.get_bank_builder(BankType.ACTION)

    @property
    def service_bank(self):
        """
        Return the ServiceBankBuilder.

        :return: the ServiceBankBuilder
        :rtype: ServiceBankBuilder
        """
        return self._ros_model_builder.get_bank_builder(BankType.SERVICE)

    @property
    def parameter_bank(self):
        """
        Return the ParameterBankBuilder.

        :return: the ParameterBankBuilder
        :rtype: ParameterBankBuilder
        """
        return self._ros_model_builder.get_bank_builder(BankType.PARAMETER)

    @property
    def machine_bank(self):
        """
        Return the MachineBankBuilder.

        :return: the MachineBankBuilder
        :rtype: MachineBankBuilder
        """
        return self._ros_model_builder.get_bank_builder(BankType.MACHINE)

    @property
    def message_specification_bank(self):
        """
        Return the SpecificationBankBuilder for Message Specifications.

         :return: the SpecificationBankBuilder for Message Specifications
         :rtype: SpecificationBankBuilder
        """
        return self._ros_specification_model[BankType.MESSAGE_SPECIFICATION]

    @property
    def service_specification_bank(self):
        """
        Return the SpecificationBankBuilder for Service Specifications.

        :return: the SpecificationBankBuilder for Service Specifications
        :rtype: SpecificationBankBuilder
        """
        return self._ros_specification_model[BankType.SERVICE_SPECIFICATION]

    @property
    def action_specification_bank(self):
        """
        Return the SpecificationBankBuilder for Action Specifications.

        :return: the SpecificationBankBuilder for Action Specifications
        :rtype: SpecificationBankBuilder
        """
        return self._ros_specification_model[BankType.ACTION_SPECIFICATION]

    @property
    def package_specification_bank(self):
        """
        Return the PackageBankBuilder.

        :return: the PackageBankBuilder
        :rtype: PackageBankBuilder
        """
        return self._ros_specification_model[BankType.PACKAGE]

    def load_specifications(self, source_folder):
        """
        Load specification model from folder.

        :param source_folder: the input folder pointing to either yaml or pickle files
        :return: True if successful, false otherwise
        """
        try:
            self._ros_specification_model = ROSModel.load_model(source_folder, True)
        except Exception:  # noqa: B902
            return False

        if self._ros_specification_model is None:
            Logger.get_logger().log(LoggerLevel.ERROR, "Specification model is None!")
            return False

        missing_spec = False
        for spec_type in ROSModel.SPECIFICATION_TYPES:
            try:
                spec = self._ros_specification_model[spec_type]
                if spec is None or len(spec.keys) < 1:
                    Logger.get_logger().log(
                        LoggerLevel.ERROR,
                        f"Specification model {ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[spec_type]} is invalid!",
                    )
                    missing_spec = True
            except KeyError:
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"Specification model {ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[spec_type]} is missing!",
                )
                missing_spec = True

        return not missing_spec

    def collect_system_info(self, node, include_hidden_topics=True):
        """
        Crawl the system and collects nodes, topics, actions, & services.

        :return: information
        :rtype: tuple(dict, list, dict, dict)

        Is expecting the final result to be (per ROS1 implementation)
        state = {topic1: [node1, node2], topic2: [node3, node4], etc...}
        """
        list_of_node_names = get_node_names(node=node, include_hidden_nodes=True)

        nodes_list = []
        topics_dict = {}
        actions_dict = {}
        services_dict = {}

        node_filter = filters.NodeFilter(True, True)
        for each_node in list_of_node_names:
            node_name = each_node.full_name
            if node_filter.should_filter_out(node_name):
                continue

            nodes_list.append(each_node)

            action_servers = get_action_server_info(
                node=node, remote_node_name=node_name, include_hidden=True
            )
            for action in action_servers:
                if action.name not in actions_dict:
                    actions_dict[action.name] = {
                        "servers": set(),
                        "clients": set(),
                        "types": set(),
                    }
                actions_dict[action.name]["servers"].add(node_name)
                actions_dict[action.name]["types"].update(action.types)
            action_clients = get_action_client_info(
                node=node, remote_node_name=node_name, include_hidden=True
            )
            for action in action_clients:
                if action.name not in actions_dict:
                    actions_dict[action.name] = {
                        "servers": set(),
                        "clients": set(),
                        "types": set(),
                    }
                actions_dict[action.name]["clients"].add(node_name)
                actions_dict[action.name]["types"].update(action.types)
            publisher_topics = get_publisher_info(
                node=node, remote_node_name=node_name, include_hidden=True
            )
            for topic in publisher_topics:
                if topic.name.split("/_action")[0] in actions_dict:
                    continue
                if topic.name not in topics_dict:
                    topics_dict[topic.name] = {
                        "publishers": set(),
                        "subscribers": set(),
                        "types": set(),
                    }
                topics_dict[topic.name]["publishers"].add(node_name)
                topics_dict[topic.name]["types"].update(topic.types)

            subscriber_topics = get_subscriber_info(
                node=node, remote_node_name=node_name, include_hidden=True
            )
            for topic in subscriber_topics:
                if topic.name.split("/_action")[0] in actions_dict:
                    continue
                if topic.name not in topics_dict:
                    topics_dict[topic.name] = {
                        "publishers": set(),
                        "subscribers": set(),
                        "types": set(),
                    }
                topics_dict[topic.name]["subscribers"].add(node_name)
                topics_dict[topic.name]["types"].update(topic.types)

            service_servers = get_service_server_info(
                node=node, remote_node_name=node_name, include_hidden=True
            )
            for server in service_servers:
                if server.name not in services_dict:
                    services_dict[server.name] = {
                        "servers": set(),
                        "clients": set(),
                        "types": set(),
                    }
                services_dict[server.name]["servers"].add(node_name)
                services_dict[server.name]["types"].update(server.types)

            service_clients = get_service_server_info(
                node=node, remote_node_name=node_name, include_hidden=True
            )
            for client in service_clients:
                if client.name not in services_dict:
                    services_dict[client.name] = {
                        "servers": set(),
                        "clients": set(),
                        "types": set(),
                    }
                services_dict[client.name]["clients"].add(node_name)
                services_dict[client.name]["types"].update(client.types)

        return (actions_dict, nodes_list, services_dict, topics_dict)

    def snapshot(self):
        """
        Probe the ROS deployment to populate the ROSModel.

        Captures details of the ROS Computation Graph.

        :return: True if successful; False if failures were encountered
        :rtype: bool
        """
        try:
            with NodeStrategy(None) as node:
                try:
                    filters.NodeFilter.BASE_EXCLUSIONS.add(
                        "/" + node.direct_node.get_name()
                    )  # Filter out this snapshot node
                except Exception:  # noqa: B902
                    Logger.get_logger().log(LoggerLevel.INFO, "No DirectNode name")

                try:
                    filters.NodeFilter.BASE_EXCLUSIONS.add(
                        "/" + node.daemon_node.get_name()
                    )  # Filter out this snapshot node
                except Exception:  # noqa: B902
                    Logger.get_logger().log(LoggerLevel.INFO, "No DaemonNode name")

                self._node = node
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    "Getting system information from the ROS network ...",
                )

                system_info = self.collect_system_info(node, include_hidden_topics=True)
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    "Setting up ModelBuilder with topic information ...",
                )

                topics_list = []
                for topic_name, topic_info in system_info[-1].items():
                    topic_types = list(topic_info["types"])
                    if len(topic_types) > 1:
                        topics_list.append((topic_name, topic_types))
                    elif len(topic_types) == 1:
                        topics_list.append((topic_name, topic_types[0]))
                    else:
                        topics_list.append((topic_name, None))

                self._ros_model_builder = ROSModelBuilder(topics_list)
                Logger.get_logger().log(
                    LoggerLevel.DEBUG, "Collect ROS Computation Graph information..."
                )

                # Meat and potatoes of the snapshot
                self._collect_rosgraph_info(system_info, node)

                Logger.get_logger().log(LoggerLevel.INFO, "Prepare data banks...")

                self._ros_model_builder.prepare()

                Logger.get_logger().log(LoggerLevel.INFO, "Validate model data ...")
                self._validate_and_update_models()

                Logger.get_logger().log(
                    LoggerLevel.DEBUG, "Construct ROS Model from metamodel instances..."
                )
                self._ros_deployment_model = self._ros_model_builder.extract_model()

        except socket.error as ex:
            Logger.get_logger().log(
                LoggerLevel.ERROR, f"Cannot connect to ROS Master: {ex}."
            )
            return False
        except ValidationError as exc:
            print(f"ROS Snapshot: Pydantic Validation Error :\n    {exc}", flush=True)
            for error in exc.errors():
                print(
                    f"Loc: {error['loc']}, Msg: {error['msg']}, Type: {error['type']}",
                    flush=True,
                )
            print(exc.json())

            print(traceback.format_exc())
            return False
        Logger.get_logger().log(
            LoggerLevel.INFO, "\x1b[92mSnapshot is complete!\x1b[0m"
        )
        return True

    def _create_spec_remappers(self):
        """Create dictionary of remappers between spec banks."""
        remappers = {}

        # node exe to package/node data
        node_spec = self.ros_specification_model[BankType.NODE_SPECIFICATION]
        remappers["node_remapper"] = RemapperBank()

        node_remapper = remappers["node_remapper"]
        for _, spec in node_spec.items:
            if isinstance(spec.file_path, list):
                for file_name in spec.file_path:
                    node_remapper.add_remap(file_name, spec.name)
            else:
                node_remapper.add_remap(spec.file_path, spec.name)

        return remappers

    def _validate_and_update_models(self):
        """
        Validate node, topic, service, and action information.

        Validate information with specs and node information if needed.
        """
        # The logic in this method is not good, sort of works
        # but should be refactored at some point
        remappers = self._create_spec_remappers()

        node_remapper = remappers["node_remapper"]
        for node_key, node_builder in self.node_bank.items:
            try:
                node_spec = None
                node_spec_remap = None

                file_name = node_builder.executable_file
                try:
                    node_spec_remap = node_remapper[file_name]
                except KeyError:
                    cmdline = getattr(node_builder, "executable_cmdline", [])
                    if isinstance(cmdline, str):
                        cmdline = cmdline.split()
                    if "python" in cmdline[0]:
                        # If python, try to extract script name
                        # Allow for python, python2, or python3 as executable_name

                        try:
                            file_name = cmdline[1]
                        except IndexError:
                            pass  # will fail again, and try to invoke backup plan below

                        try:
                            node_spec_remap = node_remapper[file_name]
                            # print(
                            #     f"   Using '{file_name}' executable file for '{node_builder.executable_cmdline}' ..."
                            # )
                        except KeyError:
                            # File still failed, so try symlink
                            if os.path.islink(file_name):
                                target = os.readlink(file_name)
                                try:
                                    node_spec_remap = node_remapper[target]
                                    print(
                                        f"   Using '{target}' executable file for symlink '{file_name}' ..."
                                    )
                                    file_name = target
                                except KeyError:
                                    pass  # invoke backup plan below
                        try:
                            node_spec_remap = node_remapper[file_name]
                        except KeyError:
                            # Failed to find a file name, so try executable name
                            print(
                                f" failed  to match '{node_builder.name}' with file_name ='{file_name}'"
                                f" try '{node_builder.executable_name}' ... "
                            )
                            try:
                                node_spec_remap = node_remapper[
                                    node_builder.executable_name
                                ]
                            except KeyError:
                                try:
                                    try:
                                        executable_path = os.path.join(*cmdline[3:5])
                                    except TypeError:
                                        executable_path = "  ".join(cmdline)

                                    # Looping through all remappers to find a match to our string,
                                    # temp saving that key
                                    for remap_key in node_remapper.keys:
                                        if executable_path in remap_key:
                                            print(
                                                f"found match with '{executable_path}' for '{remap_key}' ... "
                                            )
                                            node_spec_remap = node_remapper[remap_key]
                                            break
                                except KeyError:
                                    pass
                                except Exception as exc:  # noqa: B902
                                    print(
                                        f"Exception for '{file_name}' : {cmdline}\n    {exc}"
                                    )
                                    raise exc

                if node_spec_remap is not None:
                    # Update builder with information from specification
                    node_builder.set_node_name(node_spec_remap)

                    try:
                        # Match up the spec info
                        node_spec = self._ros_specification_model[
                            BankType.NODE_SPECIFICATION
                        ][node_spec_remap]
                        if node_spec.validated:
                            # Node is identified as valid, so let's try to match up
                            is_valid = self._validate_node_builder(
                                node_key, node_builder, node_spec
                            )
                            if not is_valid:
                                Logger.get_logger().log(
                                    LoggerLevel.WARNING,
                                    f"Node '{node_key}' is validated in the spec,"
                                    "but deployment information does not match the specification!",
                                )
                        else:
                            # Node has not been validated, so get spec info from this node
                            self._update_node_specification(node_spec, node_builder)

                    except KeyError as ex:
                        raise ex
                    except Exception as ex:  # noqa: B902
                        Logger.get_logger().log(
                            LoggerLevel.ERROR,
                            f"   Failed to validate node '{node_key}'  {node_spec_remap}  !",
                        )
                        print(type(ex))
                        print(ex)
                        track = traceback.format_exc()
                        print(track)
                        sys.exit(-1)
                else:
                    self._unmatched_nodes.append(node_builder)
                    Logger.get_logger().log(
                        LoggerLevel.WARNING,
                        f"'{node_key}' - unknown executable, skipping specification validation \n"
                        f"               for '{file_name}' ('{node_builder.executable_file}',"
                        f" '{node_builder.executable_name}') ...",
                    )

            except Exception as ex:  # noqa: B902
                Logger.get_logger().log(
                    LoggerLevel.ERROR,
                    f"   Failed to process node '{node_key}'  {file_name}  !",
                )
                print(type(ex))
                print(ex)
                track = traceback.format_exc()
                print(track)
                sys.exit(-1)

    @staticmethod
    def _match_token_types(node_name, io_names, io_builders, spec_types):
        """
        Look for matched tokens and/or data types between node and spec.

        :param node_name:
        :param io_names: relevant names to process (dict)
        :param io_builders: builder for relevant type
        :param spec_types: corresponding data in specification
        :return: True if all valid, False otherwise
        """
        try:
            if spec_types is None:
                if len(io_names) > 0:
                    # Nothing defined for spec
                    return False
            else:
                # We have action clients to match up in the spec
                available_tokens = set(spec_types)
                io_is_valid = True
                for io_name in sorted(io_names):
                    builder = io_builders[io_name]
                    io_type = builder.construct_type
                    token = io_name.split("/")[-1]

                    if token not in available_tokens or io_type != spec_types[token]:
                        # look from matching item remaining tokens
                        potential = {ss for ss in available_tokens if token in ss}
                        remaining = available_tokens - potential
                        for test in sorted(potential):
                            if spec_types[test] == io_type:
                                # found match
                                io_names[io_name] = test
                                available_tokens.remove(test)
                                break
                        if io_names[io_name] is None:
                            for test in sorted(remaining):
                                if spec_types[test] == io_type:
                                    # found match
                                    io_names[io_name] = test
                                    available_tokens.remove(test)
                                    break
                        if io_names[io_name] is None:
                            # If still None, then no match found
                            Logger.get_logger().log(
                                LoggerLevel.WARNING,
                                f"      Node {node_name} unmatched data {io_name} !",
                            )
                            io_is_valid = False
                    else:
                        # Found valid match
                        io_names[io_name] = token
                        available_tokens.remove(token)

                return io_is_valid

        except Exception as ex:  # noqa: B902
            print(type(ex))
            print(ex)
            track = traceback.format_exc()
            print(track)
            sys.exit(-1)

    @staticmethod
    def list_to_io_dict(names):
        """
        Convert a list of input/output names into a dictionary with default None values.

        :param names: List of full names (e.g., parameter names) to convert
        :type names: list[str]
        :return: Dictionary mapping each name to None
        :rtype: dict[str, None]
        """
        return {name: None for name in names}

    def _validate_node_builder(self, node_name, node_builder, node_spec):
        """
        See if the node builder data matches the node spec.

        :param node_name: name of node in question
        :param node_builder: node builder instance
        :param node_spec: instance of node speciciation
        :return: True if all matches up; false if any mismatches
        """
        node_is_valid = True

        Logger.get_logger().log(LoggerLevel.DEBUG, f"Validating Node {node_name} ...")
        # Spec should define more parameters than we either read or write
        if len(node_spec.parameters) < len(node_builder.parameter_names):
            Logger.get_logger().log(
                LoggerLevel.WARNING,
                f"      Node {node_name} incorrect number of parameters to read ({len(node_builder.parameter_names)}"
                f" vs. {len(list(node_spec.parameters.keys()))})!",
            )
            node_is_valid = False

        if len(node_spec.parameters) < len(node_builder.parameter_names):
            Logger.get_logger().log(
                LoggerLevel.WARNING,
                f"      Node {node_name} incorrect number of parameters to set ({len(node_builder.parameter_names)}"
                f" vs. {len(list(node_spec.parameters.keys()))})!",
            )
            node_is_valid = False

        # All parameter names once
        parameters = node_spec.parameters
        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.parameter_names),
            self._ros_model_builder.get_bank_builder(BankType.PARAMETER),
            parameters,
        )

        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.parameter_names),
            self._ros_model_builder.get_bank_builder(BankType.PARAMETER),
            parameters,
        )

        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.action_clients),
            self._ros_model_builder.get_bank_builder(BankType.ACTION),
            node_spec.action_clients,
        )

        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.action_servers),
            self._ros_model_builder.get_bank_builder(BankType.ACTION),
            node_spec.action_servers,
        )

        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.published_topic_names),
            self._ros_model_builder.get_bank_builder(BankType.TOPIC),
            node_spec.published_topics,
        )

        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.subscribed_topic_names),
            self._ros_model_builder.get_bank_builder(BankType.TOPIC),
            node_spec.subscribed_topics,
        )

        node_is_valid = node_is_valid and self._match_token_types(
            node_name,
            self.list_to_io_dict(node_builder.service_names_with_remap),
            self._ros_model_builder.get_bank_builder(BankType.SERVICE),
            node_spec.services_provided,
        )

        return node_is_valid

    @staticmethod
    def _update_node_specification_data(spec_data, builder_data, item_builders):
        """
        Update node spec data from deployed node if unvalidated spec.

        :param spec_data: specification dictionary (name:type)
        :param builder_data: data from node builder
        :param item_builders: builder list for type
        """
        token_map = {name: 0 for name in spec_data}
        for spec_name in sorted(builder_data):
            try:
                builder = item_builders[spec_name]
                spec_type = builder.construct_type
                spec_token = spec_name.split("/")[-1]

                if spec_token in spec_data:
                    # Just store as string unless multiple
                    token_map[spec_token] += 1
                    spec_token += "_" + str(token_map[spec_token])
                else:
                    token_map[spec_token] = 0

                spec_data[spec_token] = spec_type
            except Exception as exc:  # noqa: B902
                print(exc)
                print(traceback.format_exc(), flush=True)
                raise exc

    def _update_node_specification(self, node_spec, node_builder):
        """
        Add details to node specification based on the first deployed node of that type.

        :param node_builder: node builder instance
        :param node_spec: instance of node speciciation
        :return: True if all matches up; false if any mismatches
        """
        assert not node_spec.validated
        self.specification_update = True

        Logger.get_logger().log(LoggerLevel.INFO, "Updating node specification")

        parameters = node_spec.parameters
        if parameters is None:
            parameters = {}
        self._update_node_specification_data(
            parameters,
            node_builder.parameter_names,
            self._ros_model_builder.get_bank_builder(BankType.PARAMETER),
        )

        set_parameters = node_spec.parameters
        if set_parameters is None:
            set_parameters = {}
        self._update_node_specification_data(
            set_parameters,
            node_builder.parameter_names,
            self._ros_model_builder.get_bank_builder(BankType.PARAMETER),
        )
        parameters.update(set_parameters)

        action_clients = node_spec.action_clients
        if action_clients is None:
            action_clients = {}
        self._update_node_specification_data(
            action_clients,
            node_builder.action_clients,
            self._ros_model_builder.get_bank_builder(BankType.ACTION),
        )

        action_servers = node_spec.action_servers
        if action_servers is None:
            action_servers = {}
        self._update_node_specification_data(
            action_servers,
            node_builder.action_servers,
            self._ros_model_builder.get_bank_builder(BankType.ACTION),
        )

        published_topics = node_spec.published_topics
        if published_topics is None:
            published_topics = {}
        self._update_node_specification_data(
            published_topics,
            node_builder.published_topic_names,
            self._ros_model_builder.get_bank_builder(BankType.TOPIC),
        )

        subscribed_topics = node_spec.subscribed_topics
        if subscribed_topics is None:
            subscribed_topics = {}
        self._update_node_specification_data(
            subscribed_topics,
            node_builder.subscribed_topic_names,
            self._ros_model_builder.get_bank_builder(BankType.TOPIC),
        )

        services_provided = node_spec.services_provided
        if services_provided is None:
            services_provided = {}
        self._update_node_specification_data(
            services_provided,
            node_builder.service_names_with_remap,
            self._ros_model_builder.get_bank_builder(BankType.SERVICE),
        )

        # Update the specification to include I/O data
        node_spec.update_attributes(
            validated=True,
            source="ros_snapshot",
            parameters=parameters,
            action_clients=action_clients,
            action_servers=action_servers,
            published_topics=published_topics,
            subscribed_topics=subscribed_topics,
            services_provided=services_provided,
            version=0,
        )
        assert node_spec.validated

    @property
    def ros_deployment_model(self):
        """
        Return the ROSModel instance of deployment models.

        :return: the ROSModel instance, if called after the snapshot
            method; Otherwise, None
        :rtype: ROSModel
        """
        return self._ros_deployment_model

    @property
    def ros_specification_model(self):
        """
        Return the ROSModel instance of specifications.

        :return: the ROSModel instance, if called after the snapshot
            method; Otherwise, None
        :rtype: ROSModel
        """
        return self._ros_specification_model

    def _collect_rosgraph_info(self, state_information, node):
        """
        Collect ROS graph information.

        Helper method to populate the internal ROSModelBuilder and its
        BankBuilders with details about the ROS Computation Graph

        :param state_information: The tuple of Published Topic names to
            Node names, Subscribed Topic names to Node names, and
            Service names to Node names
        :param node used to access ROS network
        :type state_information: tuple(dict{str: list[str]}, dict{str: list[str]}, dict{str: list[str]})
        """
        actions, nodes, services, topics = state_information

        Logger.get_logger().log(
            LoggerLevel.DEBUG, "Creating Nodes with Topic Information..."
        )

        self._create_nodes_with_topics(topics, node, nodes)
        Logger.get_logger().log(
            LoggerLevel.DEBUG, "Collecting Component Nodes Information..."
        )

        self._collect_component_info(node)
        Logger.get_logger().log(LoggerLevel.DEBUG, "Collecting Action Information...")

        self._collect_actions_info(actions)
        Logger.get_logger().log(LoggerLevel.DEBUG, "Collecting Services Information...")

        self._collect_services_info(services)
        Logger.get_logger().log(
            LoggerLevel.DEBUG, "Collecting Parameters Information..."
        )
        self._collect_parameters_info(node)

    def _collect_component_info(self, node):
        """
        Collect component info based off of strategy node.

        :param: node object
        :type: StrategyNode
        """
        container_node_names = find_container_node_names(
            node=node, node_names=get_node_names(node=node)
        )

        # Set Node as ComponentManager
        for name in container_node_names:
            manager_name = name.full_name
            components_list = []
            results = get_components_in_container(
                node=node, remote_container_node_name=manager_name
            )

            self.node_bank[manager_name].set_manager_yaml(True)
            # Set ComponentManager Nodes as Components
            for component in results[1]:
                self.node_bank[component.name].set_comp_yaml(True, manager_name)
                components_list.append(component.name)
            # Adds list of component names to ComponentManagers
            self.node_bank[manager_name].set_component_list(components_list)

    def _create_nodes_with_topics(self, topics_information, node, nodes):
        """
        Create nodes with topic info.

        Helper method to create NodeBuilders and TopicBuilders within
        the ROSModelBuilder's NodeBankBuilder and TopicBankBuilder,
        respectively

        :param topics_information: Topic names to information  {pub, sub, types} dictionary
        :type topics_information: {pub, sub, types} dictionary
        """
        for each_node in nodes:
            self.node_bank[each_node.full_name].add_info(each_node)

        for topic_name, topic_info in topics_information.items():
            self._gid_dict = {}
            for info in node.get_publishers_info_by_topic(topic_name):
                self._gid_dict[info.node_name] = 0
                self.topic_bank[topic_name].get_verbose_info(
                    info, self._gid_dict
                )  # this is the verbose information we want
            collected_topic = self.topic_bank[topic_name]
            for info in node.get_subscriptions_info_by_topic(topic_name):
                self._gid_dict[info.node_name] = 0
                self.topic_bank[topic_name].get_verbose_info(
                    info, self._gid_dict
                )  # this is the verbose information we want
            for node_name in topic_info["publishers"]:
                collected_topic.add_node_name(node_name, "published")
                self.node_bank[node_name].add_topic_name(
                    topic_name, "published", collected_topic.construct_type, None
                )
            for node_name in topic_info["subscribers"]:
                collected_topic.add_node_name(node_name, "subscribed")
                self.node_bank[node_name].add_topic_name(
                    topic_name, "subscribed", collected_topic.construct_type, None
                )

    def _collect_actions_info(self, actions_information):
        """
        Collect action info.

        Helper method to create NodeBuilders and ActionBuilders within
        the ROSModelBuilder's NodeBankBuilder and ActionBankBuilder,
        respectively

        :param actions_information: Topic names to information  {servers, clients, types} dictionary
        :type actions_information: dict{str: list[str]}
        """
        action_dict = actions_information.items()

        for action_name, action_info in action_dict:
            self.action_bank[action_name].add_info(action_info)

            for client in list(action_info["clients"]):
                self.node_bank[client].add_action_client(action_name)
            for server in list(action_info["servers"]):
                self.node_bank[server].add_action_server(action_name)

    def _collect_services_info(self, service_information):
        """
        Collect services info.

        Helper method to create NodeBuilders and ServiceBuilders within
        the ROSModelBuilder's NodeBankBuilder and ServiceBankBuilder,
        respectively

        :param service_information: Service names to {servers, clients, types} dictionary
        :type dictionary of {servers, clients, types}
        """
        for service_name, service_info in service_information.items():
            collected_service = self.service_bank[service_name]
            service_types = list(service_info["types"])
            if len(service_types) == 1:
                service_types = service_types[0]

            for node_name in service_info["servers"]:
                collected_service.add_service_provider_node_name(node_name)
                self.node_bank[node_name].add_service_name_and_type(
                    service_name, service_types
                )

    def timeout_call_list_params(self, node, node_name, timeout=2):
        """
        Bypass parameter freezing when invoking ros2 param list.

        :node: NodeStrategy object
        :node_name: name of node
        :timeout: How long to wait until we override call_list_param hang error
        """
        try:

            def target(result_holder):
                result_holder[0] = call_list_parameters(
                    node=node, node_name=node_name.full_name, prefixes=None
                )

            result_holder = [None]
            thread = threading.Thread(target=target, args=(result_holder,))
            thread.start()
            thread.join(timeout)

            if thread.is_alive():
                print(
                    f"Timeout occurred calling list parameters for '{node_name.full_name}'!"
                    " Cancelling the task and returning None ...",
                    flush=True,
                )
                # Note: Python does not provide a direct way to kill a thread.
                # We are setting the result to None manually, and returning.
                print(result_holder, flush=True)
                result = None

            else:
                result = result_holder[0]

            return result
        except Exception:  # noqa: B902
            print(f"Exception in timeout_call_list_params for '{node_name.full_name}'")
            return None

    def _collect_parameters_info(self, node):
        """
        Collect parameters info.

        Helper method to create ParameterBuilders within the
        ROSModelBuilder's ParameterBankBuilder and to map parameters to
        associated NodeBuilders (obtained from the ROS Master API)

        :param node: StrategyNode Object
        """
        print("Collecting parameter information ...", flush=True)
        params = {}

        node_names = get_node_names(node=node, include_hidden_nodes=False)
        for node_name in node_names:

            # params[node_name.full_name] = self.timeout_call_list_params(
            #     node,
            #     node_name,
            # )

            # if param_timeout is not None:
            #     params[node_name.full_name] = param_timeout
            # else:
            #     params[node_name.full_name] = "cannot_gather_param info"

            params[node_name.full_name] = call_list_parameters(
                node=node,
                node_name=node_name.full_name,
                prefixes=None,
            )

        for node_name in sorted(params.keys()):
            response = params[node_name]
            if response is None:
                print(
                    "Wait for service timed out waiting for "
                    f"parameter services for node {node_name}"
                )
                continue
            elif response.result() is None:
                e = response.exception()
                print("Exception while calling service of node " f"'{node_name}': {e}")
                continue
            response = response.result().result.names
            response = sorted(response)

            def get_parameter_values(node, node_name, params):
                """
                Return a node's parameter values.

                :node: Strategy Node object to investigate
                :node_name: node name to find parameters of
                :params:
                :returns:
                :rtype:
                """
                response = call_get_parameters(
                    node=node, node_name=node_name, parameter_names=params
                )

                # requested parameter not set
                if response is None or not response.values:
                    print(
                        f"'{node_name}' - Failed to retrieve some values.\n"
                        "        Try one at a time ..."
                    )
                    values = []
                    for p in params:
                        response = call_get_parameters(
                            node=node, node_name=node_name, parameter_names=[p]
                        )
                        if response is None or not response.values:
                            print(f"        '{p}' - Failed to retrieve parameter value")
                            values.append(None)
                        else:
                            values.append(get_value(parameter_value=response.values[0]))
                    return values
                return [get_value(parameter_value=i) for i in response.values]

            parameter_values = get_parameter_values(node, node_name, response)
            if parameter_values is None:
                print(
                    f"Failed to get_parameters for node '{node_name}'!",
                    flush=True,
                )
                continue

            for param_name, pval in zip(response, parameter_values):
                param_info = param_name, pval, node_name

                param_full_name = os.path.join(node_name, param_name)
                self.node_bank[node_name].add_parameter_name(param_full_name)
                self.parameter_bank[param_full_name].add_info(param_info)

            new_response = call_describe_parameters(
                node=node, node_name=node_name, parameter_names=response
            )
            for descriptors in new_response.descriptors:
                descriptors_full_name = os.path.join(node_name, descriptors.name)
                self.parameter_bank[descriptors_full_name].add_description(descriptors)

    def print_statistics(self):
        """Print statistics."""
        print("     --- Specifications ---")
        for bank_type in ROSModel.SPECIFICATION_TYPES:
            bank = self._ros_specification_model[bank_type]
            print(
                f"     {len(bank.keys):4d}  items in {ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]}"
            )

        print("     --- Deployment ---")
        for bank_type in ROSModel.DEPLOYMENT_TYPES:
            bank = self._ros_deployment_model[bank_type]
            print(
                f"     {len(bank.keys):4d} items in {ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]}"
            )

    def find_unmatched_executables(self):
        """
        Find unmatched executables.

        :return: List of possible executables that match the unmatched nodes
        :rtype: list[str]
        """
        possible_executable = []

        for proc in NodeBuilder.get_processes().values():
            if proc["assigned"] is None:
                possible_executable.append(proc)

        return possible_executable

    def print_unmatched(self):
        """Print unmatched nodes and executables if there are any."""
        print()
        print(30 * "=")
        Logger.get_logger().log(
            LoggerLevel.INFO,
            "Matched Executables: ...",
        )

        for proc in NodeBuilder.get_processes().values():
            if proc["assigned"] is not None:
                print(
                    f"\t  - {proc['reason']} {proc['pid']} {proc['name']}"
                    f" <{proc['assigned']}> {proc['exe']} {proc['cmdline']} "
                )

        if self._unmatched_nodes:
            executables = ROSSnapshot.find_unmatched_executables(self)

            Logger.get_logger().log(
                LoggerLevel.WARNING,
                "Unmatched nodes exist ...",
            )

            print("\tUnmatched Nodes:")
            for node in self._unmatched_nodes:
                print(f"\t  - {node.node}")

            print("\tUnmatched Executables:")
            for proc in executables:
                print(
                    f"\t  - {proc['reason']} {proc['pid']} {proc['name']} {proc['exe']} {proc['cmdline']}"
                )

        print(30 * "=", flush=True)


def get_options(argv):
    """
    Handle command line options.

    :param argv: command arguments
    """
    parser = argparse.ArgumentParser(
        usage="ros2 run ros2_snapshot running [options]",
        description="""
        Probe ROS deployment to retrieve snap of
        ROS computation graph\n and create model using snapshot_modeling metamodels
        """.strip(),
    )

    parser.add_argument(
        "-a",
        "--all",
        dest="all",
        default=False,
        action="store_true",
        help="output all possible formats",
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        default="~/.snapshot_modeling",
        type=str,
        action="store",
        help="target output directory (default='~/.snapshot_modeling')",
    )
    parser.add_argument(
        "-r",
        "--human",
        dest="human",
        default=None,
        type=str,
        action="store",
        help="output human readable text format to directory (default=None)",
    )
    parser.add_argument(
        "-y",
        "--yaml",
        dest="yaml",
        default="yaml",
        type=str,
        action="store",
        help="output yaml format to directory (default=`yaml`)",
    )
    parser.add_argument(
        "-p",
        "--pickle",
        dest="pickle",
        default="pickle",
        type=str,
        action="store",
        help="output pickle format to directory (default='pickle')",
    )
    parser.add_argument(
        "-j",
        "--json",
        dest="json",
        default=None,
        type=str,
        action="store",
        help="output json format to directory (default=None)",
    )
    parser.add_argument(
        "-g",
        "--graph",
        dest="graph",
        default=None,
        type=str,
        action="store",
        help="output dot format for computation graph to directory (default=None)",
    )
    parser.add_argument(
        "-d",
        "--display",
        dest="display",
        default=False,
        action="store_true",
        help="display computation graph pdf (default=False) (only if output)",
    )
    parser.add_argument(
        "-b",
        "--base",
        dest="base",
        default="snapshot",
        type=str,
        action="store",
        help="output base file name (default='snapshot')",
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        default="/snapshot",
        type=str,
        action="store",
        help="Node name for snapshot tool (default='/snapshot')",
    )
    parser.add_argument(
        "-s",
        "--spec-input",
        dest="spec",
        default="~/.snapshot_modeling/yaml",
        type=str,
        action="store",
        help="specification model input folder (default='~/.snapshot_modeling/yaml')",
    )
    parser.add_argument(
        "-v",
        "--version",
        dest="version",
        default=False,
        action="store_true",
        help="display version information",
    )
    parser.add_argument(
        "-lt",
        "--logger_threshold",
        dest="logger_threshold",
        choices={
            "ERROR": LoggerLevel.ERROR,
            "WARNING": LoggerLevel.WARNING,
            "INFO": LoggerLevel.INFO,
            "DEBUG": LoggerLevel.DEBUG,
        },
        default="INFO",
        help="logger threshold (default=`INFO`)",
    )

    options, _ = parser.parse_known_args(argv)

    if options.all:
        if options.human is None:
            options.human = "human"
        if options.json is None:
            options.json = "json"
        if options.yaml is None:
            options.yaml = "yaml"
        if options.pickle is None:
            options.pickle = "pickle"
        if options.graph is None:
            options.graph = "dot_graph"

    if not any(
        (options.yaml, options.json, options.human, options.pickle, options.graph)
    ):
        Logger.get_logger().log(LoggerLevel.ERROR, "ROS Snapshot usage error!")
        print(
            "\x1b[91m    At least one output type must be specified (or --all)!\n\x1b[96m"
        )
        parser.print_help()
        print("================================\x1b[0m", flush=True)
        sys.exit(-1)

    if options.version:
        print(parser.usage)
        try:
            from importlib.metadata import version

            print(f"ros2_snapshot:snapshot v{version('ros2_snapshot')}", flush=True)
        except Exception:  # noqa: B902
            try:
                share_dir = get_package_share_directory("ros2_snapshot")
                file_name = os.path.join(share_dir, "VERSION")
                with open(file_name) as fin:
                    v = fin.read().strip()
                print(f"ros2_snapshot:snapshot v{v}", flush=True)
            except Exception:  # noqa: B902
                print("Unknown version", flush=True)
        sys.exit(0)

    return options


def main(argv=None):
    """
    Run the ROS Snapshot tool.

    This is the driver that sets up and runs all
    of the Logging, Filtering, Probing, and Model creation
    functionality
    """
    options = get_options(argv)

    Logger.LEVEL = options.logger_threshold
    filters.NodeFilter.BASE_EXCLUSIONS.add(options.name)
    filters.Filter.FILTER_OUT_DEBUG = True
    filters.Filter.FILTER_OUT_TF = False

    start_time = time.time()

    try:
        subprocess.run(
            ["ros2", "daemon", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        pass

    Logger.get_logger().log(LoggerLevel.INFO, "Initializing ROS Snapshot tool ...")
    snapshot = ROSSnapshot(options.name)

    Logger.get_logger().log(LoggerLevel.DEBUG, "Load existing specification model ...")

    if not snapshot.load_specifications(os.path.expanduser(options.spec)):
        Logger.get_logger().log(
            LoggerLevel.ERROR, "Failed to input existing specification model ..."
        )
        print("     Run ros2_snapshot workspace to generate specification model")
        print("        use -s or --spec-input option to set the input folder ")
        print(
            "        the input code will detect either json, yaml, or pickle file inputs."
        )
        sys.exit(-1)
    else:
        if snapshot.snapshot():
            if options.yaml is not None:
                yaml_path = os.path.join(
                    os.path.expanduser(options.target), options.yaml
                )
                Logger.get_logger().log(
                    LoggerLevel.INFO,
                    f"Saving YAML files for ROS Model to '{yaml_path}' ...",
                )
                snapshot.ros_deployment_model.save_model_yaml_files(
                    yaml_path,
                    options.base,
                )
                if snapshot.specification_update:
                    snapshot.ros_specification_model.save_model_yaml_files(
                        yaml_path,
                        options.base,
                    )

            if options.json is not None:
                json_path = os.path.join(
                    os.path.expanduser(options.target), options.json
                )
                Logger.get_logger().log(
                    LoggerLevel.INFO,
                    f"Saving JSON files for ROS Model to '{json_path}' ...",
                )
                snapshot.ros_deployment_model.save_model_json_files(
                    json_path,
                    options.base,
                )
                if snapshot.specification_update:
                    snapshot.ros_specification_model.save_model_json_files(
                        json_path,
                        options.base,
                    )

            if options.pickle is not None:
                pickle_path = os.path.join(
                    os.path.expanduser(options.target), options.pickle
                )
                Logger.get_logger().log(
                    LoggerLevel.INFO,
                    f"Saving Pickle files for ROS Model to '{pickle_path}' ...",
                )
                snapshot.ros_deployment_model.save_model_pickle_files(
                    pickle_path,
                    options.base,
                )
                if snapshot.specification_update:
                    snapshot.ros_specification_model.save_model_pickle_files(
                        pickle_path,
                        options.base,
                    )

            if options.human is not None:
                human_path = os.path.join(
                    os.path.expanduser(options.target), options.human
                )
                Logger.get_logger().log(
                    LoggerLevel.INFO,
                    f"Saving Human-readable files for ROS Model to '{human_path}' ...",
                )
                snapshot.ros_deployment_model.save_model_info_files(
                    human_path,
                    options.base,
                )
                if snapshot.specification_update:
                    snapshot.ros_specification_model.save_model_info_files(
                        human_path,
                        options.base,
                    )

            if options.graph is not None:
                snapshot.ros_deployment_model.save_dot_graph_files(
                    os.path.join(os.path.expanduser(options.target), options.graph),
                    options.base,
                    show_graph=options.display,
                )

            Logger.get_logger().log(
                LoggerLevel.INFO,
                f"Finished snapshot in {time.time() - start_time:.3f} seconds",
            )
            snapshot.print_statistics()

            snapshot.print_unmatched()

        else:
            Logger.get_logger().log(
                LoggerLevel.ERROR, "Failed to extract model of ROS system ..."
            )


if __name__ == "__main__":
    main(sys.argv)
