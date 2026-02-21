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
Module for NodeBuilder.

Represent ROS Entities and are
responsible for allowing themselves to be populated with basic
information and then further populating themselves from that
information for the purpose of extracting metamodel instances
"""

import socket
import subprocess

from core.metamodels import Component, ComponentManager, Node
from core.utilities import filters
from core.utilities.logger import Logger, LoggerLevel
from core.utilities.ros_exe_filter import list_ros_like_processes

from snapshot.builders.base_builders import _EntityBuilder


class NodeBuilder(_EntityBuilder):
    """
    Define a NodeBuilder.

    Represents a ROS
    Node and is responsible for allowing itself to be
    populated with basic information relevant to a Node and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    __processes = None  # Hold list of active processes at the time of construction

    def __init__(self, name):
        """
        Instantiate an instance of the NodeBuilder.

        :param name: the name of the Node that this NodeBuilder
            represents
        :type name: str
        """
        super(NodeBuilder, self).__init__(name)

        if NodeBuilder.__processes is None:
            print("Gather active process information ...")
            NodeBuilder.__processes = {}

            procs = list_ros_like_processes()

            for proc in procs:
                NodeBuilder.__processes[proc["pid"]] = proc
                proc["proc"].cpu_percent(
                    None
                )  # Initialize counters for later calculation

            for proc in procs:
                ppid = proc["ppid"]
                if ppid in NodeBuilder.__processes:
                    NodeBuilder.__processes[ppid]["assigned"] = str(proc["pid"])

            # for proc in NodeBuilder.__processes.values():
            #     print(
            #         f"{proc}"
            #     )  # ['reason']} {proc['pid']} {proc['name']} {proc['exe']} {proc['cmdline']}" )
            # print(30 * "-", flush=True)

        self._all_topic_names = {}
        self._topic_names = {"published": {}, "subscribed": {}}
        self._topic_names_to_types = {}
        self._service_names_to_types = {}
        self._service_names_to_remap = None
        self._parameter_names = []
        self._node = None
        self._namespace = None
        self._process_dict = None
        self._machine = None

        self.isComponentManager = False
        self.isComponent = False
        self._action_names = {"server": set(), "client": set()}

    def set_component_list(self, components_list):
        """
        Set Component list.

        @TODO
        """
        self.components_list = components_list

    def set_comp_yaml(self, isTrue, manager_name):
        """
        Set Component to true or false.

        Used for differentiation later

        :param isTrue: boolean determined if self.name
        found in our
        @TODO
        """
        self.isComponent = isTrue
        self.manager_name = manager_name
        print(
            f"\x1b[94mSetting {self.name} as a component with manager {self.manager_name}!\x1b[0m"
        )

    def set_manager_yaml(self, isTrue):
        """
        Set ComponentManager to true or false.

        Used for differentiation later

        :param isTrue: boolean determined if self.name
        found in our
        :param results: component list results
        @TODO
        """
        self.isComponentManager = isTrue

    def add_info(self, node):
        """
        Set node name of the builder.

        :node: the node name of our builder
        """
        self._node = node.name
        self._namespace = node.namespace
        print(
            f"Adding info to '{self._name}' : ns='{self._namespace}' node='{self._node}'."
        )

        # Intial attempt to find PID
        if self.get_node_pid(self._namespace, self.node, guess=False) is None:
            print("    No definitive matching for process ID on first pass", flush=True)

    def prepare(self, **kwargs):
        """
        Allow this NodeBuilder to prepare its internal state.

        Used for eventual metamodel extraction; internal changes to the state
        of the class instance occur here

        :param topic_bank_builder: the TopicBankBuilder to use for
            Action-related Topic name removal (from kwargs)
        :type topic_bank_builder: TopicBankBuilder
        :param action_bank_builder: the ActionBankBuilder to use for
            Action-related Topic name removal and Action Server / Client
            reference
        :type action_bank_builder: ActionBankBuilder
        """
        Logger.get_logger().log(
            LoggerLevel.DEBUG,
            f"Preparing instance of builder for node {self.name}.",
        )
        self._gather_process_info("exe")

    @classmethod
    def get_processes(cls):
        """
        Return list of processes.

        :return: dictionary of system processes data
        :rtype: dict
        """
        return NodeBuilder.__processes

    @property
    def node(self):
        """
        Return the package/node name of this node.

        :return: package/node name
        :rtype: string
        """
        return self._node

    @property
    def namespace(self):
        """
        Return the namespace of this node.

        :return: namespace
        :rtype: string
        """
        return self._namespace

    def set_node_name(self, name):
        """
        Set the package/node name for this node.

        :param name: package/node name
        """
        print(f"Updating node '{self._name}' from '{self._node}' to '{name}'!")
        self._node = name

    @property
    def machine(
        self,
    ):
        """
        Extract the machine ID from the uri information.

        :return: machine ID as string
        """
        return socket.gethostname()

    @property
    def executable_file(self):
        """
        Return the ROS Node executable.

        :return: the ROS Node executable
        :rtype: str
        """
        return self._gather_process_info("exe")

    @property
    def executable_name(self):
        """
        Return the ROS Node executable name.

        :return: the ROS Node executable
        :rtype: str
        """
        return self._gather_process_info("name")

    @property
    def executable_cmdline(self):
        """
        Return the ROS Node executable command line.

        :return: the ROS Node executable command line
        :rtype: str
        """
        return " ".join(self._gather_process_info("cmdline"))

    @property
    def executable_num_threads(self):
        """
        Return the ROS Node executable number threads.

        :return: the ROS Node executable number threads
        :rtype: str
        """
        return self._gather_process_info("num_threads")

    @property
    def executable_cpu_percent(self):
        """
        Return the ROS Node executable cpu percent.

        :return: the ROS Node executable cpu percent
        :rtype: str
        """
        return self._gather_process_info("cpu_percent")

    @property
    def executable_memory_percent(self):
        """
        Return the ROS Node executable memory percent.

        :return: the ROS Node executable memory percent
        :rtype: str
        """
        return self._gather_process_info("memory_percent")

    @property
    def executable_memory_info(self):
        """
        Return the ROS Node executable memory_info.

        :return: the ROS Node executable memory_info
        :rtype: str
        """
        return str(self._gather_process_info("memory_info"))

    def get_node_pid(self, namespace, node_name, guess=False):
        """
        Return the PID number give node_name.

        This is a best effort "fuzzy" process given process names that do not necessarily match node names.
        It is not based on static code analysis, and needs improvement.

        :return: the ROS Node process id
        :rtype: int
        """
        possible_procs = {}
        node_parts = node_name.split("_")
        for proc in NodeBuilder.__processes.values():
            cmdline = proc["cmdline"]
            if isinstance(cmdline, list) and cmdline:
                found_ns = namespace == "/"
                found_name = proc["name"] == node_name
                if not found_ns or not found_name:
                    for cmd in cmdline:
                        last_cmd = cmd.split("/")[-1]  # split path
                        if f"__ns:={namespace}" in cmd:
                            found_ns = True

                        if node_name in last_cmd:
                            # print(f"  Matching '{node_name}' in '{last_cmd}' for '{node_name}' in {cmd}")
                            found_name = True
                        else:
                            cmd_parts = last_cmd.split("_")

                            # How many words  match
                            parts_match = [s for s in node_parts if s in last_cmd]
                            cmd_match = [s for s in cmd_parts if s in node_name]

                            if (
                                len(parts_match) >= len(node_parts) / 2
                                and len(cmd_match) >= len(cmd_parts) / 2
                            ):
                                # Majority of pieces of our node name matches a command and
                                # majority of pieces of command are present in our node name
                                # print(f"  Matching '{node_parts}' in '{cmd_parts}'"
                                #       f" for '{node_name}' in {cmd} ({parts_match}, {cmd_match})")
                                found_name = True

                if found_ns and found_name:
                    possible_procs[proc["pid"]] = proc
            else:
                print(f"Cannot process pid for {cmdline}")

        if possible_procs:
            if len(possible_procs) == 1:
                # Only relevant entry
                pid = list(possible_procs.keys())[0]
            else:
                # Multiple potential matches
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    f"\x1b[91mMultiple potential processes for '{node_name}'"
                    f" : {possible_procs.values()}\x1b[0m",
                )
                parents_to_remove = set()

                for proc in possible_procs.values():
                    ppid = proc.get("ppid")
                    if ppid in possible_procs:
                        parents_to_remove.add(ppid)

                for ppid in parents_to_remove:
                    # Remove parent processes and use child process
                    possible_procs.pop(ppid, None)

                previously_assigned = set()
                for pid, proc in possible_procs.items():
                    if proc["assigned"] is not None:
                        previously_assigned.add(pid)

                for pid in previously_assigned:
                    # Remove previously assigned processes
                    possible_procs.pop(pid, None)

                if len(possible_procs) == 0:
                    Logger.get_logger().log(
                        LoggerLevel.INFO,
                        "\x1b[91mNo unassigned potential processes available "
                        f"for '{node_name}' \n    ignoring {previously_assigned} \x1b[0m",
                    )
                    return None

                if len(possible_procs) != 1:
                    # Unexpected outcome

                    Logger.get_logger().log(
                        LoggerLevel.INFO,
                        f"\x1b[91mMultiple potential processes remain for '{node_name}' : {possible_procs.values()}\x1b[0m",
                    )
                    if not guess:
                        print("    Do not choose for now!")
                        return None  # Do not choose for now

                pid = list(possible_procs.keys())[0]  # Get one of remaining choices

            proc = possible_procs[pid]
            if proc["assigned"] is None:
                proc["assigned"] = (
                    "/".join([namespace, node_name]) if namespace != "/" else node_name
                )
            else:
                proc["assigned"] += "," + (
                    "/".join([namespace, node_name]) if namespace != "/" else node_name
                )

            print(f"    Found process pid {pid} for '{node_name}'")
            self._process_dict = NodeBuilder.__processes[pid]  # process.as_dict()

            return pid
        else:
            print(f"\033[1;31m    Failed to find process pid for '{node_name}'!\033[0m")
            print(NodeBuilder.__processes)
            return None

    def _gather_process_info(self, key):
        """
        Gather process information.

        Helper method to gather the ROS Node executable based on
        information from the ROS Master and system

        :return: the gathered ROS Node process data by key
        :rtype: str
        """
        try:
            if self._process_dict is None:
                try:
                    process_id = -1
                    try:
                        Logger.get_logger().log(
                            LoggerLevel.DEBUG,
                            f"\x1b[91mGetting Process ID for '{self.name}'\x1b[0m",
                        )

                        process_id = self.get_node_pid(
                            self.namespace, self.node, guess=True
                        )

                        if process_id is not None:
                            Logger.get_logger().log(
                                LoggerLevel.DEBUG,
                                f"\x1b[91mProcess ID SET TO: {process_id} \x1b[0m",
                            )
                        else:
                            Logger.get_logger().log(
                                LoggerLevel.DEBUG,
                                f"\x1b[91mInvalid process ID for '{self.name}' "
                                f"(ns='{self.namespace}', node='{self.node}'\x1b[0m",
                            )
                            process_id = -1

                    except subprocess.CalledProcessError as exc:
                        print(f"Failed to get process id for '{self.name}")
                        print(f" {type(exc)} : {exc.returncode}.", flush=True)
                        print(f" {type(exc)} : {exc.output}.", flush=True)

                    if process_id > 0:
                        # dictionary should be set in get_node_pid call
                        assert (
                            self._process_dict is NodeBuilder.__processes[process_id]
                        ), f"Failed to initialize process_dict for '{self.name}'"
                    else:
                        self._process_dict = {}
                except Exception as exc:  # noqa: B902
                    # Logger.get_logger().log(
                    #     LoggerLevel.WARNING,
                    #     f"Executable for node '{self.name[1::]}' cannot be retrieved",
                    # )
                    Logger.get_logger().log(
                        LoggerLevel.WARNING,
                        f"Executable for node '{self.name}' cannot be retrieved\n   {exc}",
                    )

                    self._process_dict = {}
            if key == "cpu_percent" and self._process_dict["cpu_percent"] is None:
                print(f"setting cpu percent for '{self.name}'")
                self._process_dict[key] = self._process_dict["proc"].cpu_percent(None)
            return self._process_dict[key]
        except KeyError:
            # This error is expected if we cannot retrieve the process dictionary
            if self._process_dict:
                # Otherwise, so the existing key values
                Logger.get_logger().log(
                    LoggerLevel.WARNING,
                    f"Unknown '{key}' for '{self.name}' in process dictionary "
                    f"for node '{self.name}' \n   keys={self._process_dict.keys()}",
                )
            return f"Unknown '{key}' for '{self.name}'"
        except Exception as exc:  # noqa: B902
            error_message = (
                f"Process information for {key.upper()} of node '{self.name}'"
                f"cannot be retrieved (node_builder)"
            )
            Logger.get_logger().log(
                LoggerLevel.ERROR, f"{error_message}:\n {type(exc)} {exc}."
            )
            return f"(node_builder) UNKNOWN ERROR: CANNOT RETRIEVE '{key.upper()}' FOR '{self.name}'"

    def add_parameter_name(self, parameter_name):
        """
        Associate parameters with the ROS Node.

        :param parameter_name: the name of the Parameter
        :type parameter_name: str
        """
        self._parameter_names.append(parameter_name)

    @property
    def parameter_names(self):
        """Return parameter names for metamodel extraction."""
        return self._parameter_names

    @property
    def published_topic_names(self):
        """
        Return the names of the Topics published by the ROS Node.

        :return: published Topic names
        :rtype: dict{name:remap}
        """
        return list(self._topic_names["published"].keys())

    @property
    def subscribed_topic_names(self):
        """
        Return the names of the Topics subscribed to by the ROS Node.

        :return: subscribed Topic names
        :rtype: set{str}
        """
        return list(self._topic_names["subscribed"].keys())

    @property
    def all_topic_names(self):
        """
        Return the name of all Topics either published or subscribed to by the ROS Node.

        Including those that were removed from the
        basic Published / Subscribed store since they were related to
        either a Nodelet / Nodelet Manager interaction or an Action

        :return: all Topic names
        :rtype: set{str}
        """
        return self._all_topic_names

    def add_topic_name(self, topic_name, status, topic_type, remap):
        """
        Associate a 'published' or 'subscribed' Topic with a ROS Node.

        :param topic_name: the name of the Topic
        :type topic_name: str
        :param status: the relationship or status ('subscribed' or
            'published') of the Topic to the ROS Node
        :type status: str
        :param topic_type: the ROS Topic Type
        :type topic_type: str
        :param remap: name used by node specification
        "type remap: str"
        """
        topic_filter = filters.TopicFilter.get_filter()
        if not topic_filter.should_filter_out(topic_name):
            self._all_topic_names[topic_name] = remap
            self._topic_names[status][topic_name] = remap
            self._topic_names_to_types[topic_name] = topic_type

    def add_action_client(self, action_name):
        """
        Add list of action client names to node_bank.

        :action_name: the action name
        """
        self._action_names["client"].add(action_name)

    def add_action_server(self, action_name):
        """
        Add list of action server names to node_bank.

        :action_name: the action name
        """
        self._action_names["server"].add(action_name)

    def remove_topic_name(self, topic_name, status):
        """
        Remove either a 'published' or 'subscribed' association.

        Between a Topic name and the ROS Node

        :param topic_name: the name of the Topic
        :type topic_name: str
        :param status: the relationship or status ('subscribed' or
            'published') of the Topic to the ROS Node
        :type status: str
        """
        self._topic_names[status].pop(topic_name, None)

    @property
    def topic_names_to_types(self):
        """
        Return the mapping of all added Topic names to their ROS type.

        :return: all Topic names to their mapped ROS Topic Type
        :rtype: dict{str: str}
        """
        return self._topic_names_to_types

    @property
    def service_names_to_types(self):
        """
        Return the mapping of all Service names to their Service type.

        :return: all Service names to their mapped ROS Service Type
        :rtype: dict{str: str}
        """
        return self._service_names_to_types

    @property
    def service_names(self):
        """
        Return the name of all Services associated with the ROS Node.

        :return: associated Service names
        :rtype: set{str}
        """
        return set(self.service_names_to_types.keys())

    @property
    def service_names_with_remap(self):
        """
        Return the name of all Services associated with the ROS Node.

        As dictionary to remapped service id (None at this point)

        :return: associated Service names
        :rtype: dict{str:str}
        """
        if self._service_names_to_remap is None:
            self._service_names_to_remap = list(self.service_names_to_types.keys())

        return self._service_names_to_remap

    def add_service_name_and_type(self, service_name, service_type):
        """
        Associate the name of a Service with the ROS Node.

        :param service_name: the name of the associated Service
        :type service_name: str
        :param service_type: the ROS Service type
        :type service_type: str
        """
        service_filter = filters.ServiceTypeFilter.get_filter()
        if not service_filter.should_filter_out(service_type):
            self._service_names_to_types[service_name] = service_type

    @property
    def action_servers(self):
        """
        Return the set of Action names associated to this ROS Node.

        :return: Action names where this ROS Node is a Server
        :rtype: set{str}
        """
        if self._action_names is None:
            return None
        return list(self._action_names["server"])

    @property
    def action_clients(self):
        """
        Return the set of Action names for which this ROS Node is a Client.

        :return: Action names where this ROS Node is a Client
        :rtype: set{str}
        """
        if self._action_names is None:
            return None
        return list(self._action_names["client"])

    def _populate_metamodel_with_common_info(self, node_metamodel):
        """
        Populate metamodel with common info.

        Helper method to populate a Node-based metamodel with all of
        the common fields that a Node has

        :param node_metamodel: the Node to populate
        :type node_metamodel: Node
        :return: the same Node reference (for chained calls)
        :rtype: Node
        """
        node_metamodel.update_attributes(
            name=self.name,
            node=self.node,
            namespace=self.namespace,
            executable_name=self.executable_name,
            executable_file=self.executable_file,
            cmdline=self.executable_cmdline,
            num_threads=self.executable_num_threads,
            cpu_percent=self.executable_cpu_percent,
            memory_percent=self.executable_memory_percent,
            memory_info=self.executable_memory_info,
            published_topic_names=self.published_topic_names,
            subscribed_topic_names=self.subscribed_topic_names,
            action_servers=self.action_servers,
            action_clients=self.action_clients,
            provided_services=self.service_names_with_remap,
            parameter_names=self.parameter_names,
        )
        return node_metamodel

    def extract_metamodel(self):
        """
        Extract metamodel.

        Allows the NodeBuilder to create / extract either a
        Node, or Component Manager,
        instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: Node or ComponentManager
        """
        Logger.get_logger().log(LoggerLevel.INFO, f"Extracting Node for {self.name}...")
        if self.isComponentManager:
            node_metamodel = ComponentManager(source="ros_snapshot")
            node_metamodel.add_components_list(self.components_list)
        elif self.isComponent:
            node_metamodel = Component(source="ros_snapshot")
            node_metamodel.set_manager_node(self.manager_name)
        else:
            node_metamodel = Node(source="ros_snapshot")
        return self._populate_metamodel_with_common_info(node_metamodel)
