#
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

import json
import socket
from types import SimpleNamespace

from ros2_snapshot.snapshot import snapshot_remote as remote_module
from ros2_snapshot.snapshot import snapshot as snapshot_module


def test_normalize_hostname_for_namespace():
    assert (
        remote_module.normalize_hostname_for_namespace("robot-a.local")
        == "robot_a_local"
    )
    assert remote_module.normalize_hostname_for_namespace("7bot") == "host_7bot"


def test_remote_service_name_uses_namespace_scoped_service_path():
    assert (
        remote_module.remote_service_name("/robot_a") == "/robot_a/get_process_snapshot"
    )
    assert (
        remote_module.remote_service_name("robot_a") == "/robot_a/get_process_snapshot"
    )


def test_remote_options_preserve_ros_arguments():
    options = remote_module.get_options(
        [
            "--hostname",
            "robot_a",
            "--ros-args",
            "-r",
            "__ns:=/robot_a",
        ]
    )

    assert options.hostname == "robot_a"
    assert options.ros_args == ["--ros-args", "-r", "__ns:=/robot_a"]


def test_snapshot_remote_node_name_from_namespace_scoped_service():
    assert (
        snapshot_module.ROSSnapshot._snapshot_remote_node_name(
            "/robot_a/get_process_snapshot"
        )
        == "/robot_a/ros2_snapshot_remote"
    )
    assert (
        snapshot_module.ROSSnapshot._snapshot_remote_node_name(
            "/robot_a/ros2_snapshot_remote/get_process_snapshot"
        )
        == "/robot_a/ros2_snapshot_remote"
    )


def test_snapshot_remote_machine_name_uses_service_namespace():
    assert (
        snapshot_module.ROSSnapshot._snapshot_remote_machine_name(
            "/robot_a/get_process_snapshot", "cloned-host"
        )
        == "robot_a"
    )
    assert (
        snapshot_module.ROSSnapshot._snapshot_remote_machine_name(
            "/fleet/robot_a/ros2_snapshot_remote/get_process_snapshot",
            "cloned-host",
        )
        == "fleet:robot_a"
    )


def test_serialize_process_returns_json_safe_remote_record():
    process = {
        "pid": 10,
        "ppid": 1,
        "name": "talker",
        "exe": "/opt/demo/talker",
        "cmdline": ["/opt/demo/talker"],
        "num_threads": 4,
        "memory_info": SimpleNamespace(rss=1000),
        "memory_percent": 1.5,
        "reason": "test",
        "assigned": "old",
        "cpu_percent": None,
    }

    serialized = remote_module.serialize_process(process, "robot_a")

    json.dumps(serialized)
    assert serialized["machine"] == "robot_a"
    assert serialized["assigned"] is None
    assert serialized["cmdline"] == ["/opt/demo/talker"]


def test_process_snapshot_payload_samples_cpu_percent(monkeypatch):
    sleeps = []

    class Process:
        def cpu_percent(self, interval):
            assert interval is None
            return 12.5

    process = {
        "pid": 10,
        "ppid": 1,
        "name": "talker",
        "exe": "/opt/demo/talker",
        "cmdline": ["/opt/demo/talker"],
        "num_threads": 4,
        "memory_info": SimpleNamespace(rss=1000),
        "memory_percent": 1.5,
        "reason": "test",
        "assigned": None,
        "cpu_percent": None,
        "proc": Process(),
    }
    monkeypatch.setattr(
        remote_module,
        "list_ros_like_processes",
        lambda prime_cpu=True: [process],
    )
    monkeypatch.setattr(
        remote_module.time,
        "sleep",
        lambda delay: sleeps.append(delay),
    )

    payload = remote_module.build_process_snapshot_payload(
        "robot_a",
        ["192.0.2.10"],
        cpu_sample_delay_sec=0.25,
    )

    assert sleeps == [0.25]
    assert payload["processes"][0]["cpu_percent"] == 12.5
    assert "proc" not in payload["processes"][0]


def test_process_snapshot_payload_includes_ros_network_environment(monkeypatch):
    monkeypatch.setattr(
        remote_module,
        "list_ros_like_processes",
        lambda prime_cpu=True: [],
    )
    for key in remote_module.ROS_NETWORK_ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ROS_DOMAIN_ID", "96")
    monkeypatch.setenv("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp")
    monkeypatch.setenv("ROS_PACKAGE_PATH", "/opt/ros/demo")

    payload = remote_module.build_process_snapshot_payload(
        "robot_a",
        ["10.126.17.10"],
        cpu_sample_delay_sec=0,
    )

    assert payload["ros_network_environment"] == {
        "ROS_DOMAIN_ID": "96",
        "RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp",
    }
    assert payload["ros_network_address_hints"] == []


def test_process_snapshot_payload_includes_resolved_ros_network_address_hints(
    monkeypatch,
    tmp_path,
):
    config_path = tmp_path / "cyclonedds.xml"
    config_path.write_text('<Peer Address="10.126.17.131"/>')
    monkeypatch.setattr(
        remote_module,
        "list_ros_like_processes",
        lambda prime_cpu=True: [],
    )
    for key in remote_module.ROS_NETWORK_ENVIRONMENT_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CYCLONEDDS_URI", str(config_path))

    payload = remote_module.build_process_snapshot_payload(
        "robot_a",
        ["10.126.17.10"],
        cpu_sample_delay_sec=0,
    )

    assert payload["ros_network_environment"] == {"CYCLONEDDS_URI": str(config_path)}
    assert payload["ros_network_address_hints"] == ["10.126.17.131"]


def test_process_snapshot_payload_skips_cpu_percent_when_delay_is_zero(monkeypatch):
    sleeps = []

    class Process:
        info = {
            "pid": 10,
            "ppid": 1,
            "name": "talker",
            "cmdline": ["/opt/ros/demo/talker"],
            "num_threads": 4,
            "memory_info": SimpleNamespace(rss=1000),
            "memory_percent": 1.5,
        }

        def exe(self):
            return "/opt/ros/demo/talker"

        def cpu_percent(self, interval):
            raise AssertionError("cpu percent should not be sampled")

    monkeypatch.setattr(
        remote_module.psutil,
        "process_iter",
        lambda attrs=None: [Process()],
    )
    monkeypatch.setattr(
        remote_module.time,
        "sleep",
        lambda delay: sleeps.append(delay),
    )

    payload = remote_module.build_process_snapshot_payload(
        "robot_a",
        ["192.0.2.10"],
        cpu_sample_delay_sec=0,
    )

    assert sleeps == []
    assert payload["processes"][0]["cpu_percent"] is None
    assert "proc" not in payload["processes"][0]


def test_remote_classify_process_drops_ros_daemon_and_site_packages_only_processes():
    class Process:
        def __init__(self, *, name, cmdline, exe):
            self.info = {
                "pid": 10,
                "ppid": 1,
                "name": name,
                "cmdline": cmdline,
                "num_threads": 1,
                "memory_info": "rss=1000",
                "memory_percent": 0.0,
            }
            self._exe = exe

        def exe(self):
            return self._exe

        def cpu_percent(self, interval):
            raise AssertionError("cpu percent should not be sampled")

    ros_daemon = Process(
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
    qt_process = Process(
        name="QtWebEngineProcess",
        cmdline=[
            "/home/demo/venv/lib/python3.12/site-packages/PySide6/Qt/libexec/"
            "QtWebEngineProcess"
        ],
        exe="/home/demo/venv/lib/python3.12/site-packages/PySide6/Qt/libexec/"
        "QtWebEngineProcess",
    )

    assert remote_module.classify_process(ros_daemon) is None
    assert remote_module.classify_process(qt_process) is None


def test_remote_reports_when_contacted(monkeypatch):
    payload = {
        "hostname": "robot_a",
        "machine_id": "machine-id-a",
        "ip_addresses": ["192.0.2.10"],
        "ros_domain_id": "42",
        "rmw_implementation": "rmw_cyclonedds_cpp",
        "ros_network_address_hints": ["192.0.2.20"],
        "processes": [
            {"pid": 10, "name": "talker", "reason": "ros-token"},
            {"pid": 11, "name": "listener"},
        ],
    }
    monkeypatch.setattr(
        remote_module,
        "build_process_snapshot_payload",
        lambda hostname, ip_addresses, cpu_sample_delay_sec=0.0: payload,
    )

    logged = []
    debug_logged = []
    remote = object.__new__(remote_module.SnapshotRemote)
    remote.hostname = "robot_a"
    remote.ip_addresses = ["192.0.2.10"]
    remote.cpu_sample_delay_sec = 0.0
    remote.get_logger = lambda: SimpleNamespace(
        info=logged.append,
        debug=debug_logged.append,
    )
    response = SimpleNamespace(success=False, message="")

    result = remote.get_process_snapshot(None, response)

    assert result is response
    assert response.success is True
    assert json.loads(response.message) == payload
    assert (
        "ros2_snapshot remote contacted; returned 2 processes from 'robot_a'"
        in logged[0]
    )
    assert "machine_id: machine-id-a" in logged[0]
    assert "addresses: 192.0.2.10" in logged[0]
    assert "ros_domain_id: 42" in logged[0]
    assert "rmw_implementation: rmw_cyclonedds_cpp" in logged[0]
    assert "address_hints: 192.0.2.20" in logged[0]
    assert "processes: 10:talker(ros-token), 11:listener" in logged[0]
    assert "hostname: robot_a" not in logged[0]
    assert "hostname: robot_a" in debug_logged[0]


def test_remote_get_ip_addresses_prefers_interface_addresses_over_loopback_hostname(
    monkeypatch,
):
    monkeypatch.setattr(
        remote_module.psutil,
        "net_if_addrs",
        lambda: {
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
            "wlan0": [SimpleNamespace(family=socket.AF_INET, address="192.0.2.40")],
        },
    )
    monkeypatch.setattr(
        remote_module.socket,
        "getaddrinfo",
        lambda hostname, port: [(socket.AF_INET, None, None, None, ("127.0.1.1", 0))],
    )
    monkeypatch.setattr(
        remote_module.socket,
        "gethostbyname",
        lambda hostname: "127.0.1.1",
    )

    addresses = remote_module.get_ip_addresses("robot_a")

    assert addresses[0] == "192.0.2.40"
    assert "127.0.0.1" not in addresses
    assert "127.0.1.1" not in addresses


def test_remote_get_ip_addresses_prefers_ros_network_address_hints(
    monkeypatch, tmp_path
):
    config_path = tmp_path / "cyclonedds.xml"
    config_path.write_text(
        "<CycloneDDS><Domain><Discovery><Peers>"
        '<Peer Address="10.126.17.131"/>'
        "</Peers></Discovery></Domain></CycloneDDS>"
    )
    monkeypatch.setenv("CYCLONEDDS_URI", str(config_path))
    monkeypatch.setattr(
        remote_module.psutil,
        "net_if_addrs",
        lambda: {
            "eth0": [SimpleNamespace(family=socket.AF_INET, address="10.124.43.91")],
            "tun0": [SimpleNamespace(family=socket.AF_INET, address="10.126.17.10")],
        },
    )
    monkeypatch.setattr(
        remote_module.socket,
        "getaddrinfo",
        lambda hostname, port: [],
    )
    monkeypatch.setattr(
        remote_module.socket,
        "gethostbyname",
        lambda hostname: "127.0.1.1",
    )

    addresses = remote_module.get_ip_addresses("robot_a")

    assert addresses == ["10.126.17.10", "10.124.43.91"]


def test_snapshot_discovers_and_calls_remote_services(monkeypatch):
    monkeypatch.setattr(
        snapshot_module.filters.NodeFilter, "_runtime_exclusions", set()
    )
    monkeypatch.setattr(snapshot_module.filters.NodeFilter, "INSTANCE", None)
    payload = {
        "hostname": "robot_a",
        "ip_addresses": ["192.0.2.10"],
        "ros_network_environment": {"CYCLONEDDS_URI": "10.126.17.10"},
        "ros_network_address_hints": ["10.126.17.10"],
        "processes": [
            {
                "pid": 10,
                "ppid": 1,
                "name": "talker",
                "exe": "/opt/demo/talker",
                "cmdline": ["/opt/demo/talker"],
                "assigned": None,
            }
        ],
    }

    class Future:
        def done(self):
            return True

        def result(self):
            return SimpleNamespace(success=True, message=json.dumps(payload))

    class Client:
        def wait_for_service(self, timeout_sec=None):
            return True

        def call_async(self, request):
            return Future()

    class RuntimeNode:
        def __init__(self):
            self.destroyed = []

        def get_service_names_and_types(self):
            return [
                (
                    "/robot_a/get_process_snapshot",
                    ["std_srvs/srv/Trigger"],
                ),
                ("/other/trigger", ["std_srvs/srv/Trigger"]),
            ]

        def create_client(self, service_type, service_name):
            assert service_name == "/robot_a/get_process_snapshot"
            return Client()

        def destroy_client(self, client):
            self.destroyed.append(client)

    monkeypatch.setattr(
        snapshot_module.rclpy,
        "spin_until_future_complete",
        lambda node, future, timeout_sec=None: None,
    )

    runtime_node = RuntimeNode()
    ros_snapshot = snapshot_module.ROSSnapshot()

    processes = ros_snapshot._collect_snapshot_remote_processes(runtime_node)

    assert processes == [
        {
            "pid": 10,
            "ppid": 1,
            "name": "talker",
            "exe": "/opt/demo/talker",
            "cmdline": ["/opt/demo/talker"],
            "assigned": None,
            "machine": "robot_a",
            "machine_hostname": "robot_a",
            "machine_ip_addresses": ["192.0.2.10"],
            "machine_ros_network_environment": {"CYCLONEDDS_URI": "10.126.17.10"},
            "machine_ros_network_address_hints": ["10.126.17.10"],
        }
    ]
    assert (
        "/robot_a/ros2_snapshot_remote"
        in snapshot_module.filters.NodeFilter._runtime_exclusions
    )
    assert len(runtime_node.destroyed) == 1
