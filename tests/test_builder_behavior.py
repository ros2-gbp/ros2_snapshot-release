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

from types import SimpleNamespace

from ros2_snapshot.core import metamodels
from ros2_snapshot.snapshot.builders.action_builder import ActionBuilder
from ros2_snapshot.snapshot.builders.machine_bank_builder import MachineBankBuilder
from ros2_snapshot.snapshot.builders.machine_builder import MachineBuilder
from ros2_snapshot.snapshot.builders.node_builder import NodeBuilder, UNKNOWN_MACHINE
from ros2_snapshot.snapshot.builders.topic_bank_builder import TopicBankBuilder
from ros2_snapshot.snapshot.builders.topic_builder import TopicBuilder
from ros2_snapshot.snapshot import snapshot as snapshot_module


def patch_process_lookup(monkeypatch):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_bank_builder.list_ros_like_processes",
        lambda: [],
    )


def reset_filters(monkeypatch):
    monkeypatch.setattr(
        snapshot_module.filters.NodeFilter, "_runtime_exclusions", set()
    )
    monkeypatch.setattr(snapshot_module.filters.NodeFilter, "INSTANCE", None)
    monkeypatch.setattr(snapshot_module.filters.TopicFilter, "INSTANCE", None)
    monkeypatch.setattr(snapshot_module.filters.ServiceTypeFilter, "INSTANCE", None)


def build_process_dict():
    return {
        "exe": "/usr/bin/demo_node",
        "name": "demo_node_exec",
        "cmdline": ["demo_node_exec", "--ros-args"],
        "num_threads": 4,
        "cpu_percent": 1.5,
        "memory_percent": 2.5,
        "memory_info": "rss=1000",
    }


def build_process(
    *,
    pid,
    ppid=1,
    name,
    exe,
    cmdline,
    assigned=None,
    machine=None,
):
    proc = {
        "pid": pid,
        "ppid": ppid,
        "exe": exe,
        "name": name,
        "cmdline": cmdline,
        "num_threads": 1,
        "cpu_percent": None,
        "memory_percent": 0.0,
        "memory_info": "rss=1000",
        "assigned": assigned,
        "proc": SimpleNamespace(cpu_percent=lambda _interval=None: 0.0),
    }
    if machine is not None:
        proc["machine"] = machine
        proc["process_key"] = f"{machine}:{pid}"
    return proc


def make_topic_endpoint(
    *,
    reliability="RELIABLE",
    depth=10,
    topic_type_hash="hash",
):
    return SimpleNamespace(
        node_name="/talker",
        qos_profile=SimpleNamespace(
            durability="VOLATILE",
            deadline="0",
            liveliness="AUTOMATIC",
            liveliness_lease_duration="0",
            reliability=reliability,
            lifespan="0",
            history="KEEP_LAST",
            depth=depth,
        ),
        endpoint_gid=[1, 2, 3, 4],
        topic_type_hash=topic_type_hash,
    )


def test_topic_builder_extracts_verbose_topic_metamodel(monkeypatch):
    reset_filters(monkeypatch)

    topic_builder = TopicBuilder("/chatter")
    topic_builder.construct_type = "std_msgs/msg/String"
    topic_builder.add_node_name("/talker", "published")
    topic_builder.add_node_name("/listener", "subscribed")
    topic_builder.get_verbose_info(
        make_topic_endpoint(),
        {},
    )

    topic_model = topic_builder.extract_metamodel()

    assert isinstance(topic_model, metamodels.Topic)
    assert topic_model.construct_type == "std_msgs/msg/String"
    assert topic_model.publisher_node_names == ["/talker"]
    assert topic_model.subscriber_node_names == ["/listener"]
    assert topic_model.qos_profile["depth"] == 10
    assert topic_model.topic_hash == "hash"


def test_topic_builder_marks_ambiguous_verbose_metadata_explicitly(monkeypatch):
    reset_filters(monkeypatch)

    topic_builder = TopicBuilder("/chatter")
    topic_builder.construct_type = "std_msgs/msg/String"
    topic_builder.add_node_name("/talker", "published")
    topic_builder.add_node_name("/listener", "subscribed")
    gid_dict = {}
    topic_builder.get_verbose_info(
        make_topic_endpoint(
            reliability="RELIABLE",
            depth=10,
            topic_type_hash="hash-a",
        ),
        gid_dict,
    )
    topic_builder.get_verbose_info(
        make_topic_endpoint(
            reliability="BEST_EFFORT",
            depth=5,
            topic_type_hash="hash-b",
        ),
        gid_dict,
    )

    topic_model = topic_builder.extract_metamodel()

    assert topic_model.topic_hash == "[multiple] hash-a | hash-b"
    assert topic_model.qos_profile == {
        "[multiple]": [
            {
                "deadline": "0",
                "depth": 10,
                "durability": "VOLATILE",
                "history": "KEEP_LAST",
                "lifespan": "0",
                "liveliness": "AUTOMATIC",
                "liveliness_lease_duration": "0",
                "reliability": "RELIABLE",
            },
            {
                "deadline": "0",
                "depth": 5,
                "durability": "VOLATILE",
                "history": "KEEP_LAST",
                "lifespan": "0",
                "liveliness": "AUTOMATIC",
                "liveliness_lease_duration": "0",
                "reliability": "BEST_EFFORT",
            },
        ]
    }


def test_topic_builder_merges_depth_only_qos_differences(monkeypatch):
    reset_filters(monkeypatch)

    topic_builder = TopicBuilder("/flexbe/start_behavior")
    topic_builder.construct_type = "flexbe_msgs/msg/BehaviorSelection"
    gid_dict = {}
    topic_builder.get_verbose_info(
        make_topic_endpoint(depth=100),
        gid_dict,
    )
    topic_builder.get_verbose_info(
        make_topic_endpoint(depth=10),
        gid_dict,
    )

    topic_model = topic_builder.extract_metamodel()

    assert topic_model.qos_profile == {
        "deadline": "0",
        "depth": [10, 100],
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "lifespan": "0",
        "liveliness": "AUTOMATIC",
        "liveliness_lease_duration": "0",
        "reliability": "RELIABLE",
    }


def test_action_builder_add_info_and_extract_metamodel():
    action_builder = ActionBuilder("/demo_action")
    action_builder.add_info(
        {
            "servers": {"/server_node"},
            "clients": {"/client_node"},
            "types": {"demo_msgs/action/Demo"},
        }
    )

    action_model = action_builder.extract_metamodel()

    assert action_model.construct_type == "demo_msgs/action/Demo"
    assert set(action_model.server_node_names) == {"/server_node"}
    assert set(action_model.client_node_names) == {"/client_node"}


def test_action_builder_marks_ambiguous_types_explicitly():
    action_builder = ActionBuilder("/demo_action")
    action_builder.add_info(
        {
            "servers": {"/server_node"},
            "clients": {"/client_node"},
            "types": {"demo_msgs/action/A", "demo_msgs/action/B"},
        }
    )

    action_model = action_builder.extract_metamodel()

    assert action_model.construct_type == (
        "[multiple] demo_msgs/action/A | demo_msgs/action/B"
    )


def test_topic_bank_builder_marks_ambiguous_types_explicitly():
    topic_bank = TopicBankBuilder(
        [("/chatter", ["std_msgs/msg/String", "example_msgs/msg/String"])]
    )

    topic_builder = topic_bank["/chatter"]

    assert topic_builder.construct_type == (
        "[multiple] example_msgs/msg/String | std_msgs/msg/String"
    )


def test_action_builder_validate_action_topics_requires_core_types():
    action_builder = ActionBuilder("/demo_action")

    feedback_topic = TopicBuilder("/demo_action/feedback")
    feedback_topic.construct_type = "demo_msgs/action/DemoActionFeedback"
    goal_topic = TopicBuilder("/demo_action/goal")
    goal_topic.construct_type = "demo_msgs/action/DemoActionGoal"
    result_topic = TopicBuilder("/demo_action/result")
    result_topic.construct_type = "demo_msgs/action/DemoActionResult"

    for topic_builder in (feedback_topic, goal_topic, result_topic):
        action_builder.add_topic_builder(topic_builder)

    assert action_builder.validate_action_topic_builders() is True

    result_topic.construct_type = "std_msgs/msg/String"
    assert action_builder.validate_action_topic_builders() is False


def test_node_builder_extract_metamodel_populates_common_fields(monkeypatch):
    reset_filters(monkeypatch)
    patch_process_lookup(monkeypatch)
    monkeypatch.setattr(
        snapshot_module.filters.ServiceTypeFilter, "FILTER_OUT_DEBUG", True
    )
    monkeypatch.setattr(snapshot_module.filters.ServiceTypeFilter, "INSTANCE", None)

    node_builder = NodeBuilder("/demo_node", {})
    node_builder._node = "demo_node"
    node_builder._namespace = "/"
    node_builder._process_dict = build_process_dict()
    node_builder.add_topic_name("/chatter", "published", "std_msgs/msg/String", None)
    node_builder.add_topic_name("/input", "subscribed", "std_msgs/msg/String", None)
    node_builder.add_action_server("/demo_action")
    node_builder.add_action_client("/demo_action_client")
    node_builder.add_service_name_and_type("/demo_service", "std_srvs/srv/Empty")
    node_builder.add_service_name_and_type("/logger", "roscpp/SetLoggerLevel")
    node_builder.add_parameter_name("/demo_node/use_sim_time")

    node_model = node_builder.extract_metamodel()

    assert isinstance(node_model, metamodels.Node)
    assert node_model.name == "/demo_node"
    assert node_model.node == "demo_node"
    assert node_model.namespace == "/"
    assert node_model.executable_file == "/usr/bin/demo_node"
    assert node_model.executable_name == "demo_node_exec"
    assert node_model.cmdline == "demo_node_exec --ros-args"
    assert node_model.num_threads == 4
    assert node_model.cpu_percent == 1.5
    assert node_model.memory_percent == 2.5
    assert node_model.memory_info == "rss=1000"
    assert node_model.published_topic_names == ["/chatter"]
    assert node_model.subscribed_topic_names == ["/input"]
    assert set(node_model.action_servers) == {"/demo_action"}
    assert set(node_model.action_clients) == {"/demo_action_client"}
    assert node_model.provided_services == ["/demo_service"]
    assert node_model.parameter_names == ["/demo_node/use_sim_time"]


def test_node_builder_promotes_ros2_run_wrapper_to_matching_child():
    processes = {
        100: build_process(
            pid=100,
            name="ros2",
            exe="/usr/bin/ros2",
            cmdline=["ros2", "run", "demo_pkg", "talker"],
        ),
        101: build_process(
            pid=101,
            ppid=100,
            name="talker",
            exe="/opt/demo/talker",
            cmdline=["/opt/demo/talker"],
        ),
    }
    node_builder = NodeBuilder("/talker", processes)

    pid = node_builder.get_node_pid("/", "talker", guess=True)

    assert pid == 101
    assert node_builder._process_dict is processes[101]
    assert processes[100]["assigned"] is None
    assert processes[101]["assigned"] == "talker"


def test_node_builder_promotes_ros2_run_wrapper_to_unique_unmatched_child():
    processes = {
        100: build_process(
            pid=100,
            name="ros2",
            exe="/usr/bin/ros2",
            cmdline=["ros2", "run", "demo_pkg", "camera"],
        ),
        101: build_process(
            pid=101,
            ppid=100,
            name="python3",
            exe="/opt/demo/driver_exec",
            cmdline=["/opt/demo/opaque_runner"],
        ),
    }
    node_builder = NodeBuilder("/camera", processes)

    pid = node_builder.get_node_pid("/", "camera", guess=True)

    assert pid == 101
    assert node_builder._process_dict is processes[101]
    assert processes[100]["assigned"] is None
    assert processes[101]["assigned"] == "camera"


def test_node_builder_uses_matched_process_machine():
    processes = {
        "robot_a:101": build_process(
            pid=101,
            name="talker",
            exe="/opt/demo/talker",
            cmdline=["/opt/demo/talker"],
            machine="robot_a",
        )
    }
    node_builder = NodeBuilder("/talker", processes)

    assert node_builder.get_node_pid("/", "talker", guess=True) == "robot_a:101"
    assert node_builder.machine == "robot_a"


def test_node_builder_reports_unknown_machine_for_unmatched_distributed_node():
    node_builder = NodeBuilder(
        "/talker",
        {},
        unknown_machine_when_unmatched=True,
    )
    node_builder._process_dict = {}

    assert node_builder.machine == UNKNOWN_MACHINE


def test_node_builder_unmatched_warning_does_not_dump_process_table(caplog):
    processes = {
        "robot_a:101": build_process(
            pid=101,
            name="talker",
            exe="/opt/demo/talker",
            cmdline=["/opt/demo/talker"],
            machine="robot_a",
        )
    }
    node_builder = NodeBuilder("/listener", processes)

    with caplog.at_level(snapshot_module.LoggerLevel.WARNING):
        pid = node_builder.get_node_pid("/", "listener", guess=True)

    assert pid is None
    assert "among 1 candidate processes" in caplog.text
    assert "robot_a:101" not in caplog.text


def test_node_builder_returns_unknown_cmdline_without_character_spacing():
    node_builder = NodeBuilder("/talker", {})
    node_builder._process_dict = {}

    assert node_builder.executable_cmdline == "Unknown 'cmdline' for '/talker'"


def test_machine_builder_resolves_name_from_machine_identity(monkeypatch):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.machine_builder.socket.gethostbyname",
        lambda hostname: "192.0.2.10" if hostname == "robot_a" else "127.0.0.1",
    )
    machine_builder = MachineBuilder("robot_a")
    machine_builder.prepare(node_name="/talker")

    machine = machine_builder.extract_metamodel()

    assert machine.name == "robot_a"
    assert machine.hostname == "robot_a"
    assert machine.ip_address == "192.0.2.10"
    assert machine.node_names == ["/talker"]


def test_machine_builder_prefers_process_machine_ip_metadata():
    machine_builder = MachineBuilder("robot_a")

    machine_builder.prepare(
        node_name="/talker",
        hostname="robot_a",
        machine_id="machine-id-a",
        machine_id_source="/etc/machine-id",
        ip_addresses=["192.0.2.20"],
    )
    machine = machine_builder.extract_metamodel()

    assert machine.hostname == "robot_a"
    assert machine.machine_id == "machine-id-a"
    assert machine.machine_id_source == "/etc/machine-id"
    assert machine.ip_address == "192.0.2.20"


def test_machine_bank_builder_prefers_addresses_on_shared_machine_subnet():
    machine_bank_builder = MachineBankBuilder()
    node_builders = SimpleNamespace(
        names_to_entity_builders={
            "/local_node": SimpleNamespace(
                name="/local_node",
                machine="local_host",
                process_info={
                    "machine": "local_host",
                    "machine_id": "local-machine-id",
                    "machine_id_source": "/etc/machine-id",
                    "machine_ip_addresses": ["10.124.41.218", "10.126.17.136"],
                },
            ),
            "/remote_node": SimpleNamespace(
                name="/remote_node",
                machine="remote_host",
                process_info={
                    "machine": "remote_host",
                    "machine_ip_addresses": ["10.124.43.91", "10.126.17.10"],
                },
            ),
        }
    )

    machine_bank_builder.prepare(node_builders=node_builders)

    local_machine = machine_bank_builder["local_host"].extract_metamodel()
    remote_machine = machine_bank_builder["remote_host"].extract_metamodel()
    assert local_machine.machine_id == "local-machine-id"
    assert local_machine.machine_id_source == "/etc/machine-id"
    assert local_machine.ip_address == "10.126.17.136"
    assert remote_machine.ip_address == "10.126.17.10"


def test_machine_bank_builder_prefers_ros_network_environment_ip_hints():
    machine_bank_builder = MachineBankBuilder()
    node_builders = SimpleNamespace(
        names_to_entity_builders={
            "/local_node": SimpleNamespace(
                name="/local_node",
                machine="local_host",
                process_info={
                    "machine": "local_host",
                    "machine_ip_addresses": ["10.124.41.218", "10.126.17.136"],
                    "machine_ros_network_environment": {
                        "ROS_DISCOVERY_SERVER": "10.126.17.131:11811"
                    },
                    "machine_ros_network_address_hints": ["10.126.17.131"],
                },
            ),
            "/remote_node": SimpleNamespace(
                name="/remote_node",
                machine="remote_host",
                process_info={
                    "machine": "remote_host",
                    "machine_ip_addresses": ["10.124.43.91", "10.126.17.10"],
                    "machine_ros_network_environment": {
                        "CYCLONEDDS_URI": '<Peer Address="10.124.43.91"/>'
                    },
                    "machine_ros_network_address_hints": ["10.124.43.91"],
                },
            ),
        }
    )

    machine_bank_builder.prepare(node_builders=node_builders)

    local_machine = machine_bank_builder["local_host"].extract_metamodel()
    remote_machine = machine_bank_builder["remote_host"].extract_metamodel()
    assert local_machine.ip_address == "10.126.17.136"
    assert remote_machine.ip_address == "10.124.43.91"


def test_machine_bank_builder_prefers_ros_network_hint_subnet_for_single_machine():
    machine_bank_builder = MachineBankBuilder()
    node_builders = SimpleNamespace(
        names_to_entity_builders={
            "/local_node": SimpleNamespace(
                name="/local_node",
                machine="local_host",
                process_info={
                    "machine": "local_host",
                    "machine_ip_addresses": ["10.124.41.218", "10.126.17.136"],
                    "machine_ros_network_environment": {
                        "ROS_DISCOVERY_SERVER": "10.126.17.131:11811"
                    },
                    "machine_ros_network_address_hints": ["10.126.17.131"],
                },
            ),
        }
    )

    machine_bank_builder.prepare(node_builders=node_builders)

    local_machine = machine_bank_builder["local_host"].extract_metamodel()
    assert local_machine.ip_address == "10.126.17.136"


def test_machine_bank_builder_ignores_unresolved_ros_network_environment_file_hints():
    machine_bank_builder = MachineBankBuilder()
    node_builders = SimpleNamespace(
        names_to_entity_builders={
            "/remote_node": SimpleNamespace(
                name="/remote_node",
                machine="remote_host",
                process_info={
                    "machine": "remote_host",
                    "machine_ip_addresses": ["10.124.43.91", "10.126.17.10"],
                    "machine_ros_network_environment": {
                        "CYCLONEDDS_URI": "/remote-only/cyclonedds.xml"
                    },
                    "machine_ros_network_address_hints": ["10.126.17.131"],
                },
            ),
        }
    )

    machine_bank_builder.prepare(node_builders=node_builders)

    remote_machine = machine_bank_builder["remote_host"].extract_metamodel()
    assert remote_machine.ip_address == "10.126.17.10"


def test_node_builder_extracts_component_manager_and_component_models(monkeypatch):
    patch_process_lookup(monkeypatch)

    manager_builder = NodeBuilder("/container", {})
    manager_builder._node = "container"
    manager_builder._namespace = "/"
    manager_builder._process_dict = build_process_dict()
    manager_builder.set_manager_yaml(True)
    manager_builder.set_component_list(["/component"])

    component_builder = NodeBuilder("/component", {})
    component_builder._node = "component"
    component_builder._namespace = "/"
    component_builder._process_dict = build_process_dict()
    component_builder.set_comp_yaml(True, "/container")

    manager_model = manager_builder.extract_metamodel()
    component_model = component_builder.extract_metamodel()

    assert isinstance(manager_model, metamodels.ComponentManager)
    assert manager_model.components == ["/component"]
    assert isinstance(component_model, metamodels.Component)
    assert component_model.manager_node_name == "/container"
