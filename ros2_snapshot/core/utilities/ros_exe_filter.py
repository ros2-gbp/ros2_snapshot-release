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

"""Process system processes looking for ROS-like instances (h/t ChatGPT)."""

import ipaddress
import os
import re
import socket
import time

import psutil

from ros2_snapshot.core.utilities.logger import Logger, LoggerLevel

# --- Heuristics you can tweak ----------------------------------------------

# Things that are strong "ROS-ish" signals in a cmdline
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

# Common desktop/system/service processes you almost never want
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

# Paths that are "system-y" (but we still keep them if ROS tokens are present)
SYSTEM_PATH_PREFIXES = (
    "/usr/sbin",
    "/sbin",
    "/usr/lib/systemd",
    "/lib/systemd",
    "/usr/libexec",
)

# ROS install / workspace hints
ROS_PATH_HINTS = (
    "/opt/ros/",  # binary installs
    "/install/",
    "/build/",  # colcon workspaces
    "/ws/",
    "/ros_ws/",  # common workspace names
)

# If a process cmdline contains any of these, it's probably a shell/editor, not a node
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

# Attributes we want to retrieve
ATTRS = [
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


def _safe_cmdline(p):
    try:
        cmd = p.info.get("cmdline") or []
        # Sometimes psutil returns None / empty
        return [c for c in cmd if c]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def _exe_path(p):
    try:
        return p.exe()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ""


def looks_rosy(cmdline, exe, name):
    """Find processes that look 'ROS-like'."""
    hay = " ".join(cmdline).lower()

    if "ros2_snapshot" in hay or "ros2-daemon" in hay:
        # print(f"\tSkipping ros2_snapshot in {cmdline}")
        return False, ""

    # Strong signals: explicit ros2 invocations, python -m, launch tools, etc.
    if any(tok in hay for tok in ROS_TOKENS):
        # for tok in ROS_TOKENS:
        #     if tok in hay:
        #         print(f"   matching '{tok}' in '{hay}'!")
        return True, "ros-token"

    # Python module style: python3 -m pkg.node or python3 <.../site-packages/...>
    if cmdline and ("python" in (cmdline[0].lower())):
        if "-m" in cmdline:
            return True, "python-module"
        if any(h in hay for h in ROS_PATH_HINTS):
            # could still be non-ROS python, but often ROS nodes are here
            return True, "python-path-hint"

    # Executable path hints: /opt/ros, workspace install
    if exe and any(h in exe for h in ROS_PATH_HINTS):
        return True, "exe-path-hint"

    # Common ROS2 node executables look like single binaries under install/lib/<pkg>/<node>
    if exe and re.search(r"/install/.+/lib/.+/.+", exe):
        return True, "install-lib-layout"

    return False, ""


def is_obvious_system_noise(cmdline, exe, name):
    """Find processes that look like system standard processes."""
    n = (name or "").strip()
    if n in SYSTEM_NAME_DENY:
        return True, "system-name-deny"

    hay = " ".join(cmdline).lower()

    if any(tok in hay for tok in INTERACTIVE_DENY_TOKENS):
        # If it's a shell launching ros2, it would have ros2 tokens; this catches plain shells/editors
        if not any(tok in hay for tok in ROS_TOKENS):
            return True, "interactive-deny"

    if exe and exe.startswith(SYSTEM_PATH_PREFIXES):
        # Still allow if ROS tokens exist (e.g., /usr/bin/ros2)
        if not any(tok in hay for tok in ROS_TOKENS):
            return True, "system-path-prefix"

    return False, ""


def classify_process(p):
    """Classify processes based on whether they look ROS-like or not."""
    cmd = _safe_cmdline(p)
    name = p.info.get("name") or ""
    exe = _exe_path(p)

    if not cmd and not name:
        return None

    noise, noise_reason = is_obvious_system_noise(cmd, exe, name)
    rosy, ros_reason = looks_rosy(cmd, exe, name)

    # Keep only ROS-ish things; but drop noise unless it is explicitly ROS (like /usr/bin/ros2)
    if rosy and (not noise or "ros2" in " ".join(cmd).lower()):
        p.cpu_percent(None)  # Initialize counters for later calculation
        data = {key: p.info.get(key) or "Unknown" for key in ATTRS}
        data.update(
            {
                "exe": exe,
                "cmdline": cmd,
                "reason": ros_reason,
                "assigned": None,
                "cpu_percent": None,
                "proc": p,
            }
        )
        return data

    return None


def list_ros_like_processes():
    """Return list of ROS-like processes."""
    results = []
    for p in psutil.process_iter(attrs=ATTRS):
        try:
            item = classify_process(p)
            if item:
                results.append(item)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as exc:
            Logger.get_logger().log(LoggerLevel.WARNING, str(exc))
            pass

    # Sort for readability: launch tools first, then by name
    def key(x):
        hay = " ".join(x["cmdline"]).lower()
        return (
            (
                0
                if "ros2 launch" in hay or "roslaunch" in hay
                else 1 if "ros2 run" in hay or "rosrun" in hay else 2
            ),
            x["name"].lower(),
            x["pid"],
        )

    return sorted(results, key=key)


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


def _add_hostname_addresses(addresses, hostname):
    try:
        for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if family in (socket.AF_INET, socket.AF_INET6):
                addresses.add(_normalize_ip_address(sockaddr[0]))
    except OSError:
        pass

    try:
        addresses.add(_normalize_ip_address(socket.gethostbyname(hostname)))
    except OSError:
        pass


def _add_interface_addresses(addresses):
    try:
        interface_addresses = psutil.net_if_addrs()
    except (AttributeError, OSError):
        return

    for address_group in interface_addresses.values():
        for address in address_group:
            if address.family in (socket.AF_INET, socket.AF_INET6):
                addresses.add(_normalize_ip_address(address.address))


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


def get_ip_addresses(hostname=None, preferred_addresses=None):
    """Return non-loopback local IP addresses for machine identity."""
    addresses = set()
    _add_interface_addresses(addresses)
    if hostname:
        _add_hostname_addresses(addresses, hostname)
    sorted_addresses = sorted(
        [address for address in addresses if _is_machine_address(address)],
        key=_ip_sort_key,
    )
    return _prefer_ip_address_hints(sorted_addresses, preferred_addresses)


if __name__ == "__main__":
    print("Get ROS-like processes ...")
    procs = list_ros_like_processes()
    for r in procs:
        r["proc"].cpu_percent(None)
    print(f"  Found {len(procs)} ROS-like processes")
    time.sleep(1.0)  # Delay to capture CPU percent
    for r in procs:
        print(f'[{r["pid"]}] {r["name"]}  ({r["reason"]})')
        for key in ATTRS:
            print(f"    {key}: {r[key]}")
        print(f"    cpu_percent: {r['proc'].cpu_percent()}")
        print()
