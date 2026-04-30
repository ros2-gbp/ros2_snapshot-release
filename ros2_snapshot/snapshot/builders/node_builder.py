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

from ros2_snapshot.core.metamodels import Component, ComponentManager, Node
from ros2_snapshot.core.utilities import filters
from ros2_snapshot.core.utilities.logger import Logger, LoggerLevel
from ros2_snapshot.core.utilities.ros_exe_filter import list_ros_like_processes

from ros2_snapshot.snapshot.builders.base_builders import _EntityBuilder


UNKNOWN_MACHINE = "UNKNOWN MACHINE"


class NodeBuilder(_EntityBuilder):
    """
    Define a NodeBuilder.

    Represents a ROS
    Node and is responsible for allowing itself to be
    populated with basic information relevant to a Node and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    def __init__(self, name, processes, unknown_machine_when_unmatched=False):
        """
        Instantiate an instance of the NodeBuilder.

        :param name: the name of the Node that this NodeBuilder represents
        :param processes: shared dict of pid→process data for this snapshot run,
            supplied by NodeBankBuilder so all builders see the same assignments
        """
        super(NodeBuilder, self).__init__(name)
        self._processes = processes
        self._unknown_machine_when_unmatched = unknown_machine_when_unmatched

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
        Logger.get_logger().log(
            LoggerLevel.INFO,
            f"\x1b[94mSetting {self.name} as a component with manager {self.manager_name}!\x1b[0m",
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
        Logger.get_logger().log(
            LoggerLevel.DEBUG,
            f"Adding info to '{self._name}' : ns='{self._namespace}' node='{self._node}'.",
        )

        # Intial attempt to find PID
        if self.get_node_pid(self._namespace, self.node, guess=False) is None:
            Logger.get_logger().log(
                LoggerLevel.DEBUG,
                "    No definitive matching for process ID on first pass",
            )

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
        Logger.get_logger().log(
            LoggerLevel.DEBUG,
            f"Updating node '{self._name}' from '{self._node}' to '{name}'!",
        )
        self._node = name

    @property
    def machine(
        self,
    ):
        """
        Extract the machine ID from the uri information.

        :return: machine ID as string
        """
        if self._process_dict is not None and self._process_dict.get("machine"):
            return self._process_dict["machine"]
        if self._unknown_machine_when_unmatched:
            return UNKNOWN_MACHINE
        return socket.gethostname()

    @property
    def process_info(self):
        """Return the matched process metadata for this node, if available."""
        return self._process_dict or {}

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
        cmdline = self._gather_process_info("cmdline")
        if isinstance(cmdline, (list, tuple)):
            return " ".join(str(arg) for arg in cmdline)
        return cmdline

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

    @staticmethod
    def _is_ros_run_wrapper(proc):
        """Return True when proc looks like a ros2 run/rosrun launcher wrapper."""
        cmdline = proc.get("cmdline")
        if not isinstance(cmdline, list):
            return False
        haystack = " ".join(str(arg) for arg in cmdline).lower()
        return "ros2 run" in haystack or "rosrun" in haystack

    def _unique_unassigned_child_key(self, parent_proc):
        parent_pid = parent_proc.get("pid")
        parent_machine = parent_proc.get("machine")
        child_keys = [
            process_key
            for process_key, proc in self._processes.items()
            if (
                proc.get("ppid") == parent_pid
                and proc.get("machine") == parent_machine
                and proc.get("assigned") is None
            )
        ]
        if len(child_keys) != 1:
            return None
        return child_keys[0]

    @staticmethod
    def _same_machine_parent(candidate_proc, parent_proc):
        return candidate_proc.get("ppid") == parent_proc.get(
            "pid"
        ) and candidate_proc.get("machine") == parent_proc.get("machine")

    def _candidate_parent_keys(self, possible_procs):
        return {
            parent_key
            for parent_key, parent_proc in possible_procs.items()
            for proc in possible_procs.values()
            if self._same_machine_parent(proc, parent_proc)
        }

    def _promote_ros_run_wrappers(self, possible_procs, proc_match_scores):
        for pid, proc in list(possible_procs.items()):
            if not self._is_ros_run_wrapper(proc):
                continue

            child_pid = self._unique_unassigned_child_key(proc)
            if child_pid is None or child_pid not in self._processes:
                continue

            possible_procs[child_pid] = self._processes[child_pid]
            proc_match_scores[child_pid] = proc_match_scores[pid]
            possible_procs.pop(pid, None)
            proc_match_scores.pop(pid, None)

    def get_node_pid(self, namespace, node_name, guess=False):
        """
        Return the PID number give node_name.

        This is a best effort "fuzzy" process given process names that do not necessarily match node names.
        It is not based on static code analysis, and needs improvement.

        :return: the ROS Node process id
        :rtype: int
        """
        possible_procs = {}
        proc_match_scores = (
            {}
        )  # pid -> best node_parts count matched across all cmdline args
        node_parts = node_name.split("_")
        for process_key, proc in self._processes.items():
            cmdline = proc["cmdline"]
            if isinstance(cmdline, list) and cmdline:
                found_ns = namespace == "/"
                found_name = proc["name"] == node_name
                best_parts_matched = len(node_parts) if found_name else 0
                if not found_ns or not found_name:
                    explicit_node_remap = None
                    for cmd in cmdline:
                        last_cmd = cmd.split("/")[-1]  # split path
                        if f"__ns:={namespace}" in cmd:
                            found_ns = True

                        if "__node:=" in cmd:
                            # __node:= is an authoritative declaration of the node name;
                            # match it exactly and skip substring/fuzzy matching for this arg.
                            explicit_node_remap = cmd.split("__node:=", 1)[1].strip()
                            if explicit_node_remap == node_name:
                                found_name = True
                                best_parts_matched = len(node_parts)
                            continue

                        if node_name in last_cmd:
                            # print(f"  Matching '{node_name}' in '{last_cmd}' for '{node_name}' in {cmd}")
                            found_name = True
                            best_parts_matched = len(node_parts)
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
                                best_parts_matched = max(
                                    best_parts_matched, len(parts_match)
                                )

                    # If the process explicitly remapped to a different node name,
                    # override any fuzzy/substring match — this process is not for node_name.
                    if (
                        explicit_node_remap is not None
                        and explicit_node_remap != node_name
                    ):
                        found_name = False

                if found_ns and found_name:
                    possible_procs[process_key] = proc
                    proc_match_scores[process_key] = best_parts_matched
            else:
                Logger.get_logger().log(
                    LoggerLevel.WARNING, f"Cannot process pid for {cmdline}"
                )

        self._promote_ros_run_wrappers(possible_procs, proc_match_scores)

        # Prefer higher-quality matches: drop candidates that matched fewer node_parts
        # than the best candidate before attempting further disambiguation.
        if len(possible_procs) > 1:
            max_score = max(proc_match_scores.values())
            weaker = [
                pid for pid, score in proc_match_scores.items() if score < max_score
            ]
            for pid in weaker:
                possible_procs.pop(pid)
                proc_match_scores.pop(pid)

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
                parents_to_remove = self._candidate_parent_keys(possible_procs)

                for parent_key in parents_to_remove:
                    # Remove parent processes and use child process
                    possible_procs.pop(parent_key, None)

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
                        Logger.get_logger().log(
                            LoggerLevel.DEBUG, "    Do not choose for now!"
                        )
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

            Logger.get_logger().log(
                LoggerLevel.DEBUG, f"    Found process pid {pid} for '{node_name}'"
            )
            self._process_dict = self._processes[pid]

            return pid
        else:
            level = LoggerLevel.WARNING if guess else LoggerLevel.DEBUG
            Logger.get_logger().log(
                level,
                f"Failed to find process pid for '{node_name}' "
                f"among {len(self._processes)} candidate processes.",
            )
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
                        Logger.get_logger().log(
                            LoggerLevel.ERROR,
                            f"Failed to get process id for '{self.name}': "
                            f"{type(exc)} returncode={exc.returncode} output={exc.output}",
                        )

                    if process_id is not None and process_id in self._processes:
                        # dictionary should be set in get_node_pid call
                        assert (
                            self._process_dict is self._processes[process_id]
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
                process = self._process_dict.get("proc")
                if process is not None:
                    Logger.get_logger().log(
                        LoggerLevel.DEBUG, f"setting cpu percent for '{self.name}'"
                    )
                    self._process_dict[key] = process.cpu_percent(None)
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
