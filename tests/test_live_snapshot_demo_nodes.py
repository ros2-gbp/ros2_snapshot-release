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

import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import pytest

pytest.importorskip("apt")
pytest.importorskip("rclpy")

from ament_index_python.packages import PackageNotFoundError
from ament_index_python.packages import get_package_prefix

from ros2cli.node.strategy import NodeStrategy
from ros2node.api import get_node_names
from ros2node.api import get_publisher_info

from ros2_snapshot.core.ros_model import ROSModel
from ros2_snapshot.snapshot import snapshot as snapshot_module
from ros2_snapshot.workspace_modeler import workspace_modeler as workspace_module


def _require_demo_environment():
    if shutil.which("ros2") is None:
        pytest.skip("ros2 CLI is not available in PATH")
    if not os.environ.get("AMENT_PREFIX_PATH"):
        pytest.skip("ROS environment is not sourced")
    try:
        get_package_prefix("demo_nodes_py")
    except PackageNotFoundError:
        pytest.skip("demo_nodes_py package is not available")


def _get_demo_executable_path(executable_name):
    executable_path = (
        Path(get_package_prefix("demo_nodes_py"))
        / "lib"
        / "demo_nodes_py"
        / executable_name
    )
    if not executable_path.is_file():
        pytest.skip(f"demo_nodes_py executable is not available: {executable_name}")
    return executable_path


def _require_live_graph_access():
    try:
        with NodeStrategy(None) as node:
            get_node_names(
                node=node,
                include_hidden_nodes=True,
            )
    except Exception as exc:
        if "Operation not permitted" in str(exc):
            pytest.skip(
                "Live ROS graph access is blocked in this environment "
                f"({type(exc).__name__}: {exc})"
            )
        raise


def _start_demo_node(executable_name):
    return subprocess.Popen(
        [str(_get_demo_executable_path(executable_name))],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def _describe_process_exit(process, process_name):
    stdout, stderr = process.communicate(timeout=1)
    details = [f"{process_name} exited early with code {process.returncode}"]
    if stdout:
        details.append(f"{process_name} stdout:\n{stdout.strip()}")
    if stderr:
        details.append(f"{process_name} stderr:\n{stderr.strip()}")
    return "\n".join(details)


def _stop_process(process):
    if process.poll() is not None:
        return

    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def _wait_for_demo_graph(talker, listener, timeout_sec=20.0):
    deadline = time.time() + timeout_sec
    observed_nodes = set()
    last_error = None

    while time.time() < deadline:
        if talker.poll() is not None:
            pytest.fail(_describe_process_exit(talker, "demo_nodes_py talker"))
        if listener.poll() is not None:
            pytest.fail(_describe_process_exit(listener, "demo_nodes_py listener"))

        try:
            with NodeStrategy(None) as node:
                observed_nodes = {
                    node_name.full_name
                    for node_name in get_node_names(
                        node=node,
                        include_hidden_nodes=True,
                    )
                }
                if "/talker" not in observed_nodes or "/listener" not in observed_nodes:
                    time.sleep(0.5)
                    continue

                publisher_info = get_publisher_info(
                    node=node,
                    remote_node_name="/talker",
                    include_hidden=True,
                )
                if any(endpoint.name == "/chatter" for endpoint in publisher_info):
                    return
        except Exception as exc:
            if "Operation not permitted" in str(exc):
                pytest.skip(
                    "Live ROS graph access is blocked in this environment "
                    f"({type(exc).__name__}: {exc})"
                )
            last_error = f"{type(exc).__name__}: {exc}"

        time.sleep(0.5)

    pytest.fail(
        "Timed out waiting for demo_nodes_py talker/listener to appear in the "
        "ROS graph. "
        f"Observed nodes: {sorted(observed_nodes)}. "
        f"Last probe error: {last_error}"
    )


def test_workspace_and_running_capture_demo_nodes_graph(tmp_path, monkeypatch):
    _require_demo_environment()

    specs_root = Path(tmp_path) / "workspace_model"
    snapshot_root = Path(tmp_path) / "snapshot_model"
    log_root = Path(tmp_path) / "ros_logs"
    log_root.mkdir()
    monkeypatch.setenv("ROS_LOG_DIR", str(log_root))
    _require_live_graph_access()

    subprocess.run(
        ["ros2", "daemon", "start"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    workspace_module.main(
        [
            "--target",
            str(specs_root),
            "--logger_threshold",
            "ERROR",
        ]
    )

    spec_input = specs_root / "yaml"
    assert spec_input.exists()

    talker = _start_demo_node("talker")
    listener = _start_demo_node("listener")

    try:
        _wait_for_demo_graph(talker, listener)

        snapshot_module.main(
            [
                "--target",
                str(snapshot_root),
                "--spec-input",
                str(spec_input),
                "--logger_threshold",
                "ERROR",
            ]
        )
    finally:
        _stop_process(listener)
        _stop_process(talker)

    deployment_model = ROSModel.load_model(snapshot_root / "yaml")

    assert deployment_model is not None
    assert "/talker" in deployment_model.node_bank.keys
    assert "/listener" in deployment_model.node_bank.keys
    assert "/chatter" in deployment_model.topic_bank.keys

    chatter = deployment_model.topic_bank["/chatter"]
    assert chatter.construct_type == "std_msgs/msg/String"
    assert "/talker" in chatter.publisher_node_names
    assert "/listener" in chatter.subscriber_node_names
