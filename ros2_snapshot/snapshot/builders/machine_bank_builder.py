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

import ipaddress

from ros2_snapshot.core.metamodels import MachineBank
from ros2_snapshot.snapshot.builders.base_builders import _BankBuilder
from ros2_snapshot.snapshot.builders.machine_builder import MachineBuilder


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

    @staticmethod
    def _ipv4_subnet_key(address):
        """Return an IPv4 /24 subnet key for cross-machine network matching."""
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError:
            return None
        if parsed_address.version != 4:
            return None
        return ipaddress.ip_network(f"{address}/24", strict=False)

    @classmethod
    def _shared_ipv4_subnets(cls, node_builders):
        """Return IPv4 /24 subnets represented by more than one machine."""
        subnet_machines = {}
        for node_builder in list(node_builders.names_to_entity_builders.values()):
            process_dict = node_builder.process_info
            machine = process_dict.get("machine")
            if not machine:
                continue
            for address in process_dict.get("machine_ip_addresses") or []:
                subnet_key = cls._ipv4_subnet_key(address)
                if subnet_key is None:
                    continue
                subnet_machines.setdefault(subnet_key, set()).add(machine)
        return {
            subnet_key
            for subnet_key, machines in subnet_machines.items()
            if len(machines) > 1
        }

    @classmethod
    def _prefer_shared_subnet_addresses(cls, ip_addresses, shared_subnets):
        """Order addresses so likely ROS-network addresses come first."""
        if not ip_addresses or not shared_subnets:
            return ip_addresses
        return sorted(
            ip_addresses,
            key=lambda address: (
                cls._ipv4_subnet_key(address) not in shared_subnets,
                ip_addresses.index(address),
            ),
        )

    @staticmethod
    def _prefer_environment_hint_addresses(ip_addresses, process_dict):
        """Order addresses so locally resolved ROS/DDS address hints come first."""
        if not ip_addresses:
            return ip_addresses
        hinted_addresses = process_dict.get("machine_ros_network_address_hints") or []
        if not hinted_addresses:
            return ip_addresses
        hinted_subnets = {
            MachineBankBuilder._ipv4_subnet_key(address)
            for address in hinted_addresses
            if MachineBankBuilder._ipv4_subnet_key(address)
        }
        return sorted(
            ip_addresses,
            key=lambda address: (
                address not in hinted_addresses,
                MachineBankBuilder._ipv4_subnet_key(address) not in hinted_subnets,
                ip_addresses.index(address),
            ),
        )

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
        shared_subnets = self._shared_ipv4_subnets(node_builders)
        for node_builder in list(node_builders.names_to_entity_builders.values()):
            machine_builder = self.__getitem__(node_builder.machine)
            process_dict = node_builder.process_info
            ip_addresses = self._prefer_shared_subnet_addresses(
                process_dict.get("machine_ip_addresses"), shared_subnets
            )
            ip_addresses = self._prefer_environment_hint_addresses(
                ip_addresses,
                process_dict,
            )
            machine_builder.prepare(
                node_name=node_builder.name,
                hostname=process_dict.get("machine_hostname")
                or process_dict.get("machine"),
                machine_id=process_dict.get("machine_id"),
                machine_id_source=process_dict.get("machine_id_source"),
                ip_addresses=ip_addresses,
            )
