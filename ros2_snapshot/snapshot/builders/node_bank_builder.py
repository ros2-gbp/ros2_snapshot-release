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

import socket

from ros2_snapshot.core import metamodels
from ros2_snapshot.core.utilities import filters
from ros2_snapshot.core.utilities.logger import Logger, LoggerLevel
from ros2_snapshot.core.utilities.ros_exe_filter import extract_ip_address_hints
from ros2_snapshot.core.utilities.ros_exe_filter import get_ip_addresses
from ros2_snapshot.core.utilities.ros_exe_filter import get_machine_id
from ros2_snapshot.core.utilities.ros_exe_filter import get_ros_network_environment
from ros2_snapshot.core.utilities.ros_exe_filter import list_ros_like_processes

from ros2_snapshot.snapshot.builders.base_builders import _BankBuilder
from ros2_snapshot.snapshot.builders.node_builder import NodeBuilder


class NodeBankBuilder(_BankBuilder):
    """
    Define a NodeBankBuilder.

    Responsible for collecting,
    maintaining, and populating NodeBuilders for the purpose of
    extracting metamodel instances
    """

    def __init__(self, processes=None):
        """Load the process list once and share it with all NodeBuilder instances."""
        super().__init__()
        self._has_remote_processes = processes is not None
        remote_procs = list(processes or [])
        local_machine = socket.gethostname()
        local_machine_id, local_machine_id_source = get_machine_id()
        # Always include local processes. Remote snapshots augment local data;
        # they do not replace the capture host's process table.
        local_procs = list_ros_like_processes()
        local_ros_network_environment = get_ros_network_environment()
        local_ros_network_address_hints = extract_ip_address_hints(
            local_ros_network_environment
        )
        local_ips = get_ip_addresses(
            local_machine,
            preferred_addresses=local_ros_network_address_hints,
        )
        for proc in local_procs:
            proc.setdefault("machine", local_machine)
            proc.setdefault("machine_hostname", local_machine)
            proc.setdefault("machine_id", local_machine_id)
            proc.setdefault("machine_id_source", local_machine_id_source)
            proc.setdefault("machine_ip_addresses", local_ips)
            proc.setdefault(
                "machine_ros_network_environment",
                local_ros_network_environment,
            )
            proc.setdefault(
                "machine_ros_network_address_hints",
                local_ros_network_address_hints,
            )
        procs = remote_procs + local_procs
        self._processes = self._normalize_processes(procs)

    @staticmethod
    def _process_identity_key(proc, machine):
        machine_id = proc.get("machine_id")
        if machine_id:
            return ("machine-id", machine_id, proc["pid"])
        return ("machine", machine, proc["pid"])

    @staticmethod
    def _merge_process_metadata(existing_proc, proc):
        for key, value in proc.items():
            if value in (None, "", [], {}, "Unknown"):
                continue
            if key not in existing_proc or existing_proc[key] in (
                None,
                "",
                [],
                {},
                "Unknown",
            ):
                existing_proc[key] = value
        return existing_proc

    @staticmethod
    def _normalize_processes(procs):
        processes = {}
        identity_to_key = {}
        local_machine = socket.gethostname()
        for proc in procs:
            machine = proc.get("machine") or local_machine
            proc["machine"] = machine
            proc.setdefault("machine_hostname", machine)
            identity_key = NodeBankBuilder._process_identity_key(proc, machine)
            existing_key = identity_to_key.get(identity_key)
            if existing_key is not None:
                NodeBankBuilder._merge_process_metadata(processes[existing_key], proc)
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    f"Merged duplicate process metadata for '{existing_key}'.",
                )
                continue

            process_key = proc.get("process_key") or f"{machine}:{proc['pid']}"
            if process_key in processes:
                original_key = process_key
                index = 2
                while process_key in processes:
                    process_key = f"{original_key}#{index}"
                    index += 1
                Logger.get_logger().log(
                    LoggerLevel.WARNING,
                    f"Duplicate process key '{original_key}' detected; "
                    f"recording this process as '{process_key}'.",
                )
            proc["process_key"] = process_key
            processes[process_key] = proc
            identity_to_key[identity_key] = process_key
        return processes

    @property
    def processes(self):
        """Return the shared pid→process dict for this snapshot run."""
        return self._processes

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
        return NodeBuilder(
            name,
            self._processes,
            unknown_machine_when_unmatched=self._has_remote_processes,
        )

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
