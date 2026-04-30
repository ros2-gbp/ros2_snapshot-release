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

import socket
from types import SimpleNamespace

from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.utilities import filters, ros_exe_filter


class FakeProcess:
    def __init__(self, *, pid, ppid=1, name="", cmdline=None, exe=""):
        self.info = {
            "pid": pid,
            "ppid": ppid,
            "name": name,
            "cmdline": cmdline or [],
            "num_threads": 1,
            "memory_info": "rss=1000",
            "memory_percent": 1.5,
        }
        self._exe = exe
        self.cpu_percent_calls = []

    def exe(self):
        return self._exe

    def cpu_percent(self, interval=None):
        self.cpu_percent_calls.append(interval)
        return 12.5


def test_save_dot_graph_files_renders_all_banks(monkeypatch, tmp_path):
    render_calls = []
    graph_instances = []

    class FakeBank:
        def __init__(self):
            self.graph_calls = 0

        def add_to_dot_graph(self, graph):
            self.graph_calls += 1

    class FakeDigraph:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            graph_instances.append(self)

        def render(self, filename, view=False, quiet=False):
            render_calls.append((filename, view, quiet, self.kwargs["directory"]))

    node_bank = FakeBank()
    service_bank = FakeBank()
    model = ROSModel(
        {
            BankType.NODE: node_bank,
            BankType.SERVICE: service_bank,
        }
    )

    monkeypatch.setattr("ros2_snapshot.core.ros_model.Digraph", FakeDigraph)
    monkeypatch.setattr(
        "ros2_snapshot.core.ros_model.create_directory_path",
        lambda directory_path: str(tmp_path),
    )

    model.save_dot_graph_files(tmp_path, "snapshot", show_graph=False)

    assert len(graph_instances) == 1
    assert node_bank.graph_calls == 1
    assert service_bank.graph_calls == 1
    assert render_calls == [("snapshot.dot", False, False, str(tmp_path))]


def test_save_dot_graph_files_skips_when_graphviz_python_package_missing(
    monkeypatch, tmp_path
):
    class FakeBank:
        def __init__(self):
            self.graph_calls = 0

        def add_to_dot_graph(self, graph):
            self.graph_calls += 1

    node_bank = FakeBank()
    model = ROSModel(
        {
            BankType.NODE: node_bank,
        }
    )

    monkeypatch.setattr("ros2_snapshot.core.ros_model.Digraph", None)

    model.save_dot_graph_files(tmp_path, "snapshot", show_graph=False)

    assert node_bank.graph_calls == 0


def test_node_filter_drops_namespaced_snapshot_remotes():
    node_filter = filters.NodeFilter(True, True)

    assert node_filter.should_filter_out("/robot_a/ros2_snapshot_remote") is True


def test_classify_process_returns_ros_metadata_for_ros_like_process():
    process = FakeProcess(
        pid=10,
        name="python3",
        cmdline=["python3", "-m", "demo_pkg.node"],
        exe="/usr/bin/python3",
    )

    result = ros_exe_filter.classify_process(process)

    assert result["pid"] == 10
    assert result["reason"] == "python-module"
    assert result["exe"] == "/usr/bin/python3"
    assert result["cmdline"] == ["python3", "-m", "demo_pkg.node"]
    assert result["assigned"] is None
    assert result["cpu_percent"] is None
    assert process.cpu_percent_calls == [None]


def test_classify_process_drops_interactive_noise_without_ros_signals():
    process = FakeProcess(
        pid=11,
        name="bash",
        cmdline=["bash"],
        exe="/usr/bin/bash",
    )

    assert ros_exe_filter.classify_process(process) is None


def test_classify_process_drops_ros_daemon_and_site_packages_only_processes():
    ros_daemon = FakeProcess(
        pid=12,
        name="python3",
        cmdline=[
            "python3",
            "-c",
            "from ros2cli.daemon.daemonize import main; main()",
            "--name",
            "ros2-daemon",
            "--rmw-implementation",
            "rmw_cyclonedds_cpp",
        ],
        exe="/usr/bin/python3",
    )
    qt_process = FakeProcess(
        pid=13,
        name="QtWebEngineProcess",
        cmdline=[
            "/home/demo/venv/lib/python3.12/site-packages/PySide6/Qt/libexec/"
            "QtWebEngineProcess"
        ],
        exe="/home/demo/venv/lib/python3.12/site-packages/PySide6/Qt/libexec/"
        "QtWebEngineProcess",
    )

    assert ros_exe_filter.classify_process(ros_daemon) is None
    assert ros_exe_filter.classify_process(qt_process) is None


def test_list_ros_like_processes_sorts_launch_before_run_before_other(monkeypatch):
    launch_process = FakeProcess(
        pid=1,
        name="ros2",
        cmdline=["ros2", "launch", "demo_pkg", "demo.launch.py"],
        exe="/usr/bin/ros2",
    )
    run_process = FakeProcess(
        pid=2,
        name="ros2",
        cmdline=["ros2", "run", "demo_pkg", "demo_node"],
        exe="/usr/bin/ros2",
    )
    installed_process = FakeProcess(
        pid=3,
        name="demo_node",
        cmdline=["/workspace/install/demo_pkg/lib/demo_pkg/demo_node"],
        exe="/workspace/install/demo_pkg/lib/demo_pkg/demo_node",
    )

    monkeypatch.setattr(
        ros_exe_filter.psutil,
        "process_iter",
        lambda attrs=None: [installed_process, run_process, launch_process],
    )

    results = ros_exe_filter.list_ros_like_processes()

    assert [result["pid"] for result in results] == [1, 2, 3]
    assert [result["reason"] for result in results] == [
        "ros-token",
        "ros-token",
        "exe-path-hint",
    ]


def test_get_ip_addresses_prefers_interface_addresses_over_loopback_hostname(
    monkeypatch,
):
    monkeypatch.setattr(
        ros_exe_filter.psutil,
        "net_if_addrs",
        lambda: {
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
            "eth0": [SimpleNamespace(family=socket.AF_INET, address="192.0.2.20")],
        },
    )
    monkeypatch.setattr(
        ros_exe_filter.socket,
        "getaddrinfo",
        lambda hostname, port: [(socket.AF_INET, None, None, None, ("127.0.1.1", 0))],
    )
    monkeypatch.setattr(
        ros_exe_filter.socket,
        "gethostbyname",
        lambda hostname: "127.0.1.1",
    )

    addresses = ros_exe_filter.get_ip_addresses("robot_a")

    assert addresses[0] == "192.0.2.20"
    assert "127.0.0.1" not in addresses
    assert "127.0.1.1" not in addresses


def test_ros_network_environment_filters_to_network_related_keys():
    environment = {
        "ROS_DOMAIN_ID": "96",
        "RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp",
        "ROS_PACKAGE_PATH": "/opt/ros/demo",
        "PATH": "/usr/bin",
    }

    result = ros_exe_filter.get_ros_network_environment(environment)

    assert result == {
        "ROS_DOMAIN_ID": "96",
        "RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp",
    }


def test_extract_ip_address_hints_reads_ros_network_config_files(tmp_path):
    config_path = tmp_path / "cyclonedds.xml"
    config_path.write_text(
        "<CycloneDDS><Domain><Discovery><Peers>"
        '<Peer Address="10.126.17.10"/>'
        '<Peer Address="127.0.0.1"/>'
        "</Peers></Discovery></Domain></CycloneDDS>"
    )

    result = ros_exe_filter.extract_ip_address_hints(
        {
            "CYCLONEDDS_URI": f"file://{config_path}",
            "ROS_DISCOVERY_SERVER": "10.126.17.131:11811",
        }
    )

    assert result == ["10.126.17.10", "10.126.17.131"]


def test_get_ip_addresses_prefers_ros_network_address_hints(monkeypatch):
    monkeypatch.setattr(
        ros_exe_filter.psutil,
        "net_if_addrs",
        lambda: {
            "eth0": [SimpleNamespace(family=socket.AF_INET, address="10.124.41.218")],
            "tun0": [SimpleNamespace(family=socket.AF_INET, address="10.126.17.136")],
        },
    )
    monkeypatch.setattr(
        ros_exe_filter.socket,
        "getaddrinfo",
        lambda hostname, port: [],
    )
    monkeypatch.setattr(
        ros_exe_filter.socket,
        "gethostbyname",
        lambda hostname: "127.0.1.1",
    )

    addresses = ros_exe_filter.get_ip_addresses(
        "robot_a",
        preferred_addresses=["10.126.17.131"],
    )

    assert addresses == ["10.126.17.136", "10.124.41.218"]
