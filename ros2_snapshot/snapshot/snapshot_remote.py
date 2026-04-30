#!/usr/bin/env python

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

"""Lightweight per-host process snapshot remote."""

import argparse
import ipaddress
import json
import os
import re
import socket
import time

import psutil
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
import yaml


REMOTE_NODE_NAME = "ros2_snapshot_remote"
PROCESS_SNAPSHOT_SERVICE = "get_process_snapshot"
DEFAULT_CPU_SAMPLE_DELAY_SEC = 0.25
ROS_TOKENS = [
    "ros2",
    "rclcpp",
    "rclpy",
    "launch.py",
    "ament",
    "colcon",
    "micro_ros_agent",
    "gzsim",
    "gzserver",
    "gzclient",
    "rviz",
    "rviz2",
    "robot_state_publisher",
    "controller_manager",
    "joint_state_broadcaster",
    "ros_gz",
    "gazebo_ros",
    "cyclonedds",
    "fastdds",
    "fastrtps",
    "rmw_",
]
SYSTEM_NAME_DENY = {
    "systemd",
    "systemd-journald",
    "systemd-logind",
    "dbus-daemon",
    "NetworkManager",
    "ModemManager",
    "gnome-shell",
    "Xorg",
    "Xwayland",
    "wayland",
    "pipewire",
    "wireplumber",
    "pulseaudio",
    "bluetoothd",
    "cupsd",
    "chronyd",
    "snapd",
    "packagekitd",
    "polkitd",
    "agetty",
    "udisksd",
    "upowerd",
    "landscape-manag",
    "landscape-monit",
    "gvfsd-fuse",
    "gnome-keyring-daemon",
    "gdm-x-session",
    "ros2_snapshot",
    "ros2-daemon",
}
SYSTEM_PATH_PREFIXES = (
    "/usr/sbin",
    "/sbin",
    "/usr/lib/systemd",
    "/lib/systemd",
    "/usr/libexec",
)
ROS_PATH_HINTS = (
    "/opt/ros/",
    "/install/",
    "/build/",
    "/ws/",
    "/ros_ws/",
)
INTERACTIVE_DENY_TOKENS = (
    "bash",
    "zsh",
    "fish",
    "tmux",
    "screen",
    "code",
    "vim",
    "nvim",
    "emacs",
)
PROCESS_ATTRS = [
    "pid",
    "ppid",
    "name",
    "cmdline",
    "num_threads",
    "memory_info",
    "memory_percent",
]
ROS_NETWORK_ENVIRONMENT_KEYS = (
    "ROS_DOMAIN_ID",
    "RMW_IMPLEMENTATION",
    "ROS_AUTOMATIC_DISCOVERY_RANGE",
    "ROS_STATIC_PEERS",
    "ROS_LOCALHOST_ONLY",
    "ROS_DISCOVERY_SERVER",
    "CYCLONEDDS_URI",
    "FASTRTPS_DEFAULT_PROFILES_FILE",
    "FASTDDS_DEFAULT_PROFILES_FILE",
)
MACHINE_ID_PATHS = (
    "/etc/machine-id",
    "/var/lib/dbus/machine-id",
)


def remote_service_name(namespace):
    """Return the fully qualified snapshot-remote service name."""
    normalized_namespace = namespace if namespace.startswith("/") else f"/{namespace}"
    return f"{normalized_namespace.rstrip('/')}/{PROCESS_SNAPSHOT_SERVICE}"


def _safe_cmdline(process):
    try:
        cmdline = process.info.get("cmdline") or []
        return [cmd for cmd in cmdline if cmd]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def _exe_path(process):
    try:
        return process.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ""


def looks_rosy(cmdline, exe, name):
    """Return whether a process looks ROS-like."""
    haystack = " ".join(cmdline).lower()
    if "ros2_snapshot" in haystack or "ros2-daemon" in haystack:
        return False, ""
    if any(token in haystack for token in ROS_TOKENS):
        return True, "ros-token"
    if cmdline and "python" in cmdline[0].lower():
        if "-m" in cmdline:
            return True, "python-module"
        if any(hint in haystack for hint in ROS_PATH_HINTS):
            return True, "python-path-hint"
    if exe and any(hint in exe for hint in ROS_PATH_HINTS):
        return True, "exe-path-hint"
    if exe and re.search(r"/install/.+/lib/.+/.+", exe):
        return True, "install-lib-layout"
    return False, ""


def is_obvious_system_noise(cmdline, exe, name):
    """Return whether a process looks like system noise."""
    process_name = (name or "").strip()
    if process_name in SYSTEM_NAME_DENY:
        return True, "system-name-deny"

    haystack = " ".join(cmdline).lower()
    if any(token in haystack for token in INTERACTIVE_DENY_TOKENS):
        if not any(token in haystack for token in ROS_TOKENS):
            return True, "interactive-deny"
    if exe and exe.startswith(SYSTEM_PATH_PREFIXES):
        if not any(token in haystack for token in ROS_TOKENS):
            return True, "system-path-prefix"
    return False, ""


def classify_process(process, prime_cpu=True):
    """Classify one psutil process as ROS-like or not."""
    cmdline = _safe_cmdline(process)
    name = process.info.get("name") or ""
    exe = _exe_path(process)
    if not cmdline and not name:
        return None

    noise, _ = is_obvious_system_noise(cmdline, exe, name)
    rosy, reason = looks_rosy(cmdline, exe, name)
    if rosy and (not noise or "ros2" in " ".join(cmdline).lower()):
        if prime_cpu:
            process.cpu_percent(None)
        data = {key: process.info.get(key) or "Unknown" for key in PROCESS_ATTRS}
        data.update(
            {
                "exe": exe,
                "cmdline": cmdline,
                "proc": process,
                "reason": reason,
                "assigned": None,
                "cpu_percent": None,
            }
        )
        return data
    return None


def list_ros_like_processes(prime_cpu=True):
    """Return ROS-like processes using only local psutil data."""
    results = []
    for process in psutil.process_iter(attrs=PROCESS_ATTRS):
        try:
            item = classify_process(process, prime_cpu=prime_cpu)
            if item:
                results.append(item)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def sort_key(process):
        haystack = " ".join(process["cmdline"]).lower()
        return (
            (
                0
                if "ros2 launch" in haystack or "roslaunch" in haystack
                else 1 if "ros2 run" in haystack or "rosrun" in haystack else 2
            ),
            process["name"].lower(),
            process["pid"],
        )

    return sorted(results, key=sort_key)


def get_machine_id():
    """Return a stable local machine identifier when the platform provides one."""
    for path in MACHINE_ID_PATHS:
        try:
            with open(path, "r") as machine_id_file:
                machine_id = machine_id_file.read().strip()
        except OSError:
            continue
        if machine_id:
            return machine_id, path
    return None, None


def normalize_hostname_for_namespace(hostname):
    """Return a ROS-name-safe namespace segment derived from hostname."""
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", hostname)
    normalized = normalized.strip("_")
    if not normalized:
        normalized = "unknown_host"
    if normalized[0].isdigit():
        normalized = f"host_{normalized}"
    return normalized


def get_ip_addresses(hostname):
    """Return non-loopback local IP addresses for machine identity."""
    addresses = set()
    try:
        interface_addresses = psutil.net_if_addrs()
    except (AttributeError, OSError):
        interface_addresses = {}

    for address_group in interface_addresses.values():
        for address in address_group:
            if address.family in (socket.AF_INET, socket.AF_INET6):
                normalized_address = _normalize_ip_address(address.address)
                if _is_machine_address(normalized_address):
                    addresses.add(normalized_address)

    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if family in (socket.AF_INET, socket.AF_INET6):
                normalized_address = _normalize_ip_address(sockaddr[0])
                if _is_machine_address(normalized_address):
                    addresses.add(normalized_address)
    except OSError:
        pass

    try:
        normalized_address = _normalize_ip_address(socket.gethostbyname(hostname))
        if _is_machine_address(normalized_address):
            addresses.add(normalized_address)
    except OSError:
        pass

    sorted_addresses = sorted(addresses, key=_ip_sort_key)
    return _prefer_ip_address_hints(
        sorted_addresses,
        extract_ip_address_hints(get_ros_network_environment()),
    )


def get_ros_network_environment(environ=None):
    """Return ROS/DDS environment variables that affect network discovery."""
    environ = environ if environ is not None else os.environ
    return {
        key: environ[key] for key in ROS_NETWORK_ENVIRONMENT_KEYS if environ.get(key)
    }


def _read_env_referenced_file(value):
    """Read a small local config file referenced by a ROS network env var."""
    if value.startswith("file://"):
        value = value[7:]
    if "://" in value or not os.path.exists(value):
        return ""
    try:
        with open(value, "r") as config_file:
            return config_file.read(200000)
    except OSError:
        return ""


def extract_ip_address_hints(ros_network_environment):
    """Extract usable local-network IP hints from ROS/DDS environment values."""
    values = []
    for key, value in (ros_network_environment or {}).items():
        values.append(value)
        if key in (
            "CYCLONEDDS_URI",
            "FASTRTPS_DEFAULT_PROFILES_FILE",
            "FASTDDS_DEFAULT_PROFILES_FILE",
        ):
            values.append(_read_env_referenced_file(value))

    addresses = set()
    for value in values:
        for match in re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", value):
            if _is_machine_address(match):
                addresses.add(match)
    return sorted(addresses, key=_ip_sort_key)


def _prefer_ip_address_hints(addresses, preferred_addresses):
    preferred_addresses = preferred_addresses or []
    if not preferred_addresses:
        return addresses
    preferred_subnets = {
        _ipv4_subnet_key(address)
        for address in preferred_addresses
        if _ipv4_subnet_key(address)
    }
    return sorted(
        addresses,
        key=lambda address: (
            address not in preferred_addresses,
            _ipv4_subnet_key(address) not in preferred_subnets,
            addresses.index(address),
        ),
    )


def _ipv4_subnet_key(address):
    try:
        return ipaddress.ip_network(f"{address}/24", strict=False)
    except ValueError:
        return None


def _normalize_ip_address(address):
    return address.split("%", 1)[0]


def _ip_sort_key(address):
    try:
        parsed_address = ipaddress.ip_address(_normalize_ip_address(address))
        return (parsed_address.version, str(parsed_address))
    except ValueError:
        return (99, address)


def _is_machine_address(address):
    try:
        parsed_address = ipaddress.ip_address(_normalize_ip_address(address))
        return not (
            parsed_address.is_loopback
            or parsed_address.is_link_local
            or parsed_address.is_unspecified
        )
    except ValueError:
        return False


def serialize_process(proc, machine, machine_id=None, machine_id_source=None):
    """Convert psutil-backed process data into a JSON-safe dictionary."""
    return {
        "pid": proc.get("pid"),
        "ppid": proc.get("ppid"),
        "name": proc.get("name"),
        "exe": proc.get("exe"),
        "cmdline": proc.get("cmdline") if isinstance(proc.get("cmdline"), list) else [],
        "num_threads": proc.get("num_threads"),
        "memory_info": str(proc.get("memory_info")),
        "memory_percent": proc.get("memory_percent"),
        "reason": proc.get("reason"),
        "assigned": None,
        "cpu_percent": proc.get("cpu_percent"),
        "machine": machine,
        "machine_id": machine_id,
        "machine_id_source": machine_id_source,
    }


def refresh_process_cpu_percent(proc):
    """Sample cpu_percent for a process dictionary when a psutil process is available."""
    process = proc.get("proc")
    if process is None:
        return
    try:
        proc["cpu_percent"] = process.cpu_percent(None)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        proc["cpu_percent"] = None


def build_process_snapshot_payload(
    hostname,
    ip_addresses,
    cpu_sample_delay_sec=DEFAULT_CPU_SAMPLE_DELAY_SEC,
):
    """Build the JSON-serializable process snapshot served by the remote."""
    should_sample_cpu = cpu_sample_delay_sec > 0
    raw_processes = list_ros_like_processes(prime_cpu=should_sample_cpu)
    if should_sample_cpu:
        if raw_processes:
            time.sleep(cpu_sample_delay_sec)
        for proc in raw_processes:
            refresh_process_cpu_percent(proc)

    ros_network_environment = get_ros_network_environment()
    machine_id, machine_id_source = get_machine_id()
    ros_network_address_hints = extract_ip_address_hints(ros_network_environment)
    return {
        "hostname": hostname,
        "machine_id": machine_id,
        "machine_id_source": machine_id_source,
        "ip_addresses": ip_addresses,
        "ros_network_environment": ros_network_environment,
        "ros_network_address_hints": ros_network_address_hints,
        "ros_domain_id": os.environ.get("ROS_DOMAIN_ID"),
        "rmw_implementation": os.environ.get("RMW_IMPLEMENTATION"),
        "processes": [
            serialize_process(
                proc,
                hostname,
                machine_id=machine_id,
                machine_id_source=machine_id_source,
            )
            for proc in raw_processes
        ],
    }


def _format_process_summary(processes, max_processes=12):
    """Return compact process identifiers for INFO-level remote logs."""
    process_summaries = []
    for proc in processes[:max_processes]:
        summary = f"{proc.get('pid')}:{proc.get('name')}"
        if proc.get("reason"):
            summary = f"{summary}({proc.get('reason')})"
        process_summaries.append(summary)
    if len(processes) > max_processes:
        process_summaries.append(f"... +{len(processes) - max_processes} more")
    return ", ".join(process_summaries) or "none"


def format_process_snapshot_summary(payload):
    """Return a concise human-readable summary of a remote process payload."""
    return (
        f"ros2_snapshot remote contacted; returned "
        f"{len(payload['processes'])} processes from '{payload.get('hostname')}'\n"
        f"  machine_id: {payload.get('machine_id') or 'unknown'}\n"
        f"  addresses: {', '.join(payload.get('ip_addresses') or []) or 'none'}\n"
        f"  ros_domain_id: {payload.get('ros_domain_id') or 'unset'}\n"
        f"  rmw_implementation: {payload.get('rmw_implementation') or 'unset'}\n"
        f"  address_hints: "
        f"{', '.join(payload.get('ros_network_address_hints') or []) or 'none'}\n"
        f"  processes: {_format_process_summary(payload.get('processes') or [])}"
    )


class SnapshotRemote(Node):
    """ROS node that serves local process metadata to snapshot runners."""

    def __init__(
        self,
        hostname,
        namespace,
        cpu_sample_delay_sec=DEFAULT_CPU_SAMPLE_DELAY_SEC,
    ):
        super().__init__(REMOTE_NODE_NAME, namespace=namespace)
        self.hostname = hostname
        self.ip_addresses = get_ip_addresses(hostname)
        self.cpu_sample_delay_sec = cpu_sample_delay_sec
        self.service = self.create_service(
            Trigger, PROCESS_SNAPSHOT_SERVICE, self.get_process_snapshot
        )
        self.get_logger().info(
            f"ros2_snapshot remote ready on host '{self.hostname}'\n"
            f"  namespace: {namespace}\n"
            f"  service:   {remote_service_name(namespace)}\n"
            f"  addresses: {', '.join(self.ip_addresses) or 'none discovered'}"
        )

    def get_process_snapshot(self, _request, response):
        """Return a JSON process snapshot in the Trigger message field."""
        payload = build_process_snapshot_payload(
            self.hostname,
            self.ip_addresses,
            cpu_sample_delay_sec=self.cpu_sample_delay_sec,
        )
        response.success = True
        response.message = json.dumps(payload, sort_keys=True)
        self.get_logger().info(format_process_snapshot_summary(payload))
        self.get_logger().debug(
            f"ros2_snapshot remote full process payload:\n"
            f"{yaml.safe_dump(payload, sort_keys=True)}"
        )
        return response


def get_options(argv):
    """Parse command-line options for the snapshot remote."""
    parser = argparse.ArgumentParser(
        usage="ros2 run ros2_snapshot remote [options]",
        description="Serve local process metadata for distributed ROS snapshots.",
    )
    parser.add_argument(
        "--hostname",
        default=socket.gethostname(),
        help="machine identity to report and use for default namespace",
    )
    parser.add_argument(
        "--namespace",
        default=None,
        help="remote namespace; defaults to a ROS-safe hostname namespace",
    )
    parser.add_argument(
        "--cpu-sample-delay",
        type=float,
        default=DEFAULT_CPU_SAMPLE_DELAY_SEC,
        help="seconds to wait between priming and sampling process CPU percent",
    )
    options, ros_args = parser.parse_known_args(argv)
    options.ros_args = ros_args
    return options


def main(argv=None):
    """Run the snapshot remote."""
    options = get_options(argv)
    namespace = options.namespace
    if namespace is None:
        namespace = "/" + normalize_hostname_for_namespace(options.hostname)
    elif not namespace.startswith("/"):
        namespace = "/" + namespace

    rclpy.init(args=options.ros_args)
    snapshot_remote = SnapshotRemote(
        options.hostname,
        namespace,
        cpu_sample_delay_sec=max(0.0, options.cpu_sample_delay),
    )
    try:
        rclpy.spin(snapshot_remote)
    finally:
        snapshot_remote.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
