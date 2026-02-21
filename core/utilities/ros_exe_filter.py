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

import re
import time

import psutil

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

    if "ros2_snapshot" in hay:
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
        if any(h in hay for h in ROS_PATH_HINTS) or "site-packages" in hay:
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
            print(exc)
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
