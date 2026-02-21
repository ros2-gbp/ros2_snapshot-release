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

"""Class associated with building a bank of machine models."""

import socket

from core.deployments.machine import Machine

from snapshot.builders.base_builders import _EntityBuilder


class MachineBuilder(_EntityBuilder):
    """
    Define a MachineBuilder.

    Represents a host machine running ROS nodes
     and is responsible for allowing itself to be
    populated with basic information relevant to a Machine and then
    further populating itself from that information for the purpose
    of extracting a metamodel instance
    """

    def __init__(self, name):
        """
        Instantiate an instance of the MachineBuilder.

        :param name: the name of the machine that this
            MachineBuilder represents
        :type name: str
        """
        super(MachineBuilder, self).__init__(name)
        self._hostname = None
        self._ip_address = None
        self._node_names = []

    @property
    def hostname(self):
        """
        Return the hostname of machine on network.

        :return: hostname on network
        :rtype: str
        """
        return socket.gethostname()

    @property
    def ip_address(self):
        """
        Return the ip address of given machine on network.

        :return: ip address of machine
        :rtype: str
        """
        return socket.gethostbyname(self.hostname)

    def _gather_hostname_ip(self):
        """
        Gather the hostname/IP address data.

        Using DNS and /etc/hosts as fallback.
        """
        try:
            # presume name was hostname and try to get address
            self._ip_address = socket.gethostbyname(self.name)
            self._hostname = self.name
        except Exception:  # noqa: B902
            try:
                # try the reverse
                self._hostname = socket.gethostbyaddr(self.name)[0]
                self._ip_address = self.name
            except Exception:  # noqa: B902
                nums = self.name.split(".")
                if len(nums) == 4:
                    self._ip_address = self.name
                    # Try to lookup hostname from /etc/hosts
                    hostname_found = "UNKNOWN HOSTNAME"
                    try:
                        with open("/etc/hosts", "r") as hosts_file:
                            for line in hosts_file:
                                if line.strip() and not line.startswith("#"):
                                    parts = line.split()
                                    if len(parts) > 1 and parts[0] == self.name:
                                        hostname_found = parts[1]
                                        break
                    except Exception:  # noqa: B902
                        pass
                    self._hostname = hostname_found
                else:
                    self._hostname = self.name
                    # Try to lookup IP from /etc/hosts
                    ip_found = "UNKNOWN IP ADDRESS"
                    try:
                        with open("/etc/hosts", "r") as hosts_file:
                            for line in hosts_file:
                                if line.strip() and not line.startswith("#"):
                                    parts = line.split()
                                    if len(parts) > 1 and self.name in parts[1:]:
                                        ip_found = parts[0]
                                        break
                    except Exception:  # noqa: B902
                        pass
                    self._ip_address = ip_found

    @property
    def node_names(self):
        """
        Return the collection of names of the ROS Nodes.

        Only those that have set a value for this Parameter

        :return: the collection of names of the ROS Nodes that have set
            a value for this Parameter
        :rtype: set{str}
        """
        return self._node_names

    def add_node_name(self, node_name):
        """
        Associate the name of a ROS Node to this machine.

        :param node_name: the name of the ROS Node
        :type node_name: str
        """
        if node_name not in self._node_names:
            self._node_names.append(node_name)

    def prepare(self, **kwargs):
        """
        Prepare the internal MachineBuilder.

        Based on identified nodes for eventual metamodel
        extraction; internal changes to the state of the *EntityBuilders
        occur for the builders that are stored in the internal bank

        :param kwargs: keyword arguments
        :type kwargs: dict{param: value}
        """
        self.add_node_name(kwargs["node_name"])

    def extract_metamodel(self):
        """
        Create/extract a MachineBuilder instance.

        Machine instance from its internal state

        :return: the created / extracted metamodel instance
        :rtype: Machine
        """
        machine_model = Machine(
            source="ros_snapshot",
            name=self.name,
            hostname=self.hostname,
            ip_address=self.ip_address,
            node_names=self.node_names,
        )
        return machine_model
