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
from types import SimpleNamespace

import pytest

try:
    from rclpy.endpoint_info import EndpointTypeEnum
except ImportError:
    from rclpy.topic_endpoint_info import TopicEndpointTypeEnum as EndpointTypeEnum

from ros2_snapshot.snapshot import snapshot as snapshot_module
from ros2_snapshot.snapshot.ros_model_builder import ROSModelBuilder


def make_node(full_name):
    return SimpleNamespace(
        full_name=full_name,
        name=full_name.split("/")[-1],
        namespace="/",
    )


def make_topic_endpoint(node_name, endpoint_type, endpoint_gid):
    return SimpleNamespace(
        node_name=node_name,
        qos_profile=SimpleNamespace(
            durability="VOLATILE",
            deadline="0",
            liveliness="AUTOMATIC",
            liveliness_lease_duration="0",
            reliability="RELIABLE",
            lifespan="0",
            history="KEEP_LAST",
            depth=10,
        ),
        endpoint_gid=endpoint_gid,
        endpoint_type=endpoint_type,
        topic_type_hash="hash",
    )


class FakeGraphNode:
    def __init__(self, publishers_by_topic, subscriptions_by_topic):
        self._publishers_by_topic = publishers_by_topic
        self._subscriptions_by_topic = subscriptions_by_topic

    def get_publishers_info_by_topic(self, topic_name):
        return self._publishers_by_topic.get(topic_name, [])

    def get_subscriptions_info_by_topic(self, topic_name):
        return self._subscriptions_by_topic.get(topic_name, [])


def reset_filters(monkeypatch):
    monkeypatch.setattr(
        snapshot_module.filters.NodeFilter, "BASE_EXCLUSIONS", {"/roslaunch"}
    )
    monkeypatch.setattr(snapshot_module.filters.NodeFilter, "INSTANCE", None)
    monkeypatch.setattr(snapshot_module.filters.TopicFilter, "INSTANCE", None)
    monkeypatch.setattr(snapshot_module.filters.ServiceTypeFilter, "INSTANCE", None)


def patch_process_lookup(monkeypatch):
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_builder.list_ros_like_processes",
        lambda: [],
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.node_builder.NodeBuilder.get_node_pid",
        lambda self, namespace, node_name, guess=False: None,
    )


def patch_parameter_helpers(monkeypatch, ros_snapshot, parameter_values_by_node):
    monkeypatch.setattr(
        snapshot_module,
        "get_node_names",
        lambda node, include_hidden_nodes=True: [
            make_node(node_name) for node_name in sorted(parameter_values_by_node)
        ],
    )
    monkeypatch.setattr(
        ros_snapshot,
        "_list_parameters_with_timeout",
        lambda node, node_name, timeout=2.0: SimpleNamespace(
            result=SimpleNamespace(names=sorted(parameter_values_by_node[node_name]))
        ),
    )
    monkeypatch.setattr(
        ros_snapshot,
        "_get_parameters_with_timeout",
        lambda node, node_name, parameter_names, timeout=2.0: SimpleNamespace(
            values=[
                parameter_values_by_node[node_name][param] for param in parameter_names
            ]
        ),
    )
    monkeypatch.setattr(
        ros_snapshot,
        "_describe_parameters_with_timeout",
        lambda node, node_name, parameter_names, timeout=2.0: SimpleNamespace(
            descriptors=[
                SimpleNamespace(
                    name=param,
                    description=f"{node_name}:{param}",
                )
                for param in parameter_names
            ]
        ),
    )
    monkeypatch.setattr(
        snapshot_module, "get_value", lambda parameter_value: parameter_value
    )


def test_collect_rosgraph_info_populates_banks_from_graph_data(monkeypatch):
    reset_filters(monkeypatch)
    patch_process_lookup(monkeypatch)

    ros_snapshot = snapshot_module.ROSSnapshot()
    ros_snapshot._ros_model_builder = ROSModelBuilder(
        [("/chatter", "std_msgs/msg/String")]
    )

    talker = make_node("/talker")
    listener = make_node("/listener")
    graph_node = FakeGraphNode(
        publishers_by_topic={
            "/chatter": [
                make_topic_endpoint(
                    "/talker",
                    EndpointTypeEnum.PUBLISHER,
                    [1, 2, 3, 4],
                )
            ]
        },
        subscriptions_by_topic={
            "/chatter": [
                make_topic_endpoint(
                    "/listener",
                    EndpointTypeEnum.SUBSCRIPTION,
                    [5, 6, 7, 8],
                )
            ]
        },
    )

    monkeypatch.setattr(
        snapshot_module, "find_container_node_names", lambda **kwargs: []
    )
    patch_parameter_helpers(
        monkeypatch,
        ros_snapshot,
        {
            "/listener": {"queue_size": 10},
            "/talker": {"use_sim_time": True},
        },
    )

    ros_snapshot._collect_rosgraph_info(
        (
            {
                "/demo_action": {
                    "servers": {"/talker"},
                    "clients": {"/listener"},
                    "types": {"demo_msgs/action/Demo"},
                }
            },
            [talker, listener],
            {
                "/demo_service": {
                    "servers": {"/talker"},
                    "clients": {"/listener"},
                    "types": {"std_srvs/srv/Empty"},
                }
            },
            {
                "/chatter": {
                    "publishers": {"/talker"},
                    "subscribers": {"/listener"},
                    "types": {"std_msgs/msg/String"},
                }
            },
        ),
        graph_node,
    )

    talker_builder = ros_snapshot.node_bank["/talker"]
    listener_builder = ros_snapshot.node_bank["/listener"]
    topic_builder = ros_snapshot.topic_bank["/chatter"]
    action_builder = ros_snapshot.action_bank["/demo_action"]
    service_builder = ros_snapshot.service_bank["/demo_service"]

    assert talker_builder.published_topic_names == ["/chatter"]
    assert listener_builder.subscribed_topic_names == ["/chatter"]
    assert set(talker_builder.action_servers) == {"/demo_action"}
    assert set(listener_builder.action_clients) == {"/demo_action"}
    assert talker_builder.service_names_to_types == {
        "/demo_service": "std_srvs/srv/Empty"
    }
    assert topic_builder.construct_type == "std_msgs/msg/String"
    assert topic_builder.publisher_node_names == ["/talker"]
    assert topic_builder.subscriber_node_names == ["/listener"]
    assert action_builder.construct_type == "demo_msgs/action/Demo"
    assert set(action_builder.server_node_names) == {"/talker"}
    assert set(action_builder.client_node_names) == {"/listener"}
    assert service_builder.construct_type == "std_srvs/srv/Empty"
    assert service_builder.service_provider_node_names == ["/talker"]
    assert service_builder.service_client_node_names == ["/listener"]
    assert ros_snapshot.parameter_bank["/talker/use_sim_time"].value is True
    assert ros_snapshot.parameter_bank["/listener/queue_size"].value == 10


def test_create_nodes_with_topics_uses_direct_node_for_verbose_topic_queries(
    monkeypatch,
):
    reset_filters(monkeypatch)
    patch_process_lookup(monkeypatch)

    ros_snapshot = snapshot_module.ROSSnapshot()
    ros_snapshot._ros_model_builder = ROSModelBuilder(
        [("/chatter", "std_msgs/msg/String")]
    )

    talker = make_node("/talker")
    listener = make_node("/listener")
    graph_node = FakeGraphNode(
        publishers_by_topic={
            "/chatter": [
                make_topic_endpoint(
                    "/talker",
                    EndpointTypeEnum.PUBLISHER,
                    [1, 2, 3, 4],
                )
            ]
        },
        subscriptions_by_topic={
            "/chatter": [
                make_topic_endpoint(
                    "/listener",
                    EndpointTypeEnum.SUBSCRIPTION,
                    [5, 6, 7, 8],
                )
            ]
        },
    )

    class StrategyWrapper:
        def __init__(self, direct_node):
            self.direct_node = direct_node

        def get_publishers_info_by_topic(self, topic_name):
            raise AssertionError("strategy wrapper should not serve verbose topic info")

        def get_subscriptions_info_by_topic(self, topic_name):
            raise AssertionError("strategy wrapper should not serve verbose topic info")

    ros_snapshot._create_nodes_with_topics(
        {
            "/chatter": {
                "publishers": {"/talker"},
                "subscribers": {"/listener"},
                "types": {"std_msgs/msg/String"},
            }
        },
        StrategyWrapper(graph_node),
        [talker, listener],
    )

    topic_builder = ros_snapshot.topic_bank["/chatter"]
    assert topic_builder.publisher_node_names == ["/talker"]
    assert topic_builder.subscriber_node_names == ["/listener"]
    assert topic_builder.endpoint_type == "[multiple] PUBLISHER | SUBSCRIPTION"


def test_snapshot_happy_path_extracts_deployment_model(monkeypatch):
    reset_filters(monkeypatch)
    patch_process_lookup(monkeypatch)
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.machine_builder.socket.gethostname",
        lambda: "test-host",
    )
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.builders.machine_builder.socket.gethostbyname",
        lambda hostname: "127.0.0.1",
    )

    talker = make_node("/talker")
    listener = make_node("/listener")
    graph_node = FakeGraphNode(
        publishers_by_topic={
            "/chatter": [
                make_topic_endpoint(
                    "/talker",
                    EndpointTypeEnum.PUBLISHER,
                    [1, 2, 3, 4],
                )
            ]
        },
        subscriptions_by_topic={
            "/chatter": [
                make_topic_endpoint(
                    "/listener",
                    EndpointTypeEnum.SUBSCRIPTION,
                    [5, 6, 7, 8],
                )
            ]
        },
    )

    class FakeNodeStrategy(FakeGraphNode):
        def __init__(self, *_args, **_kwargs):
            super().__init__(
                graph_node._publishers_by_topic, graph_node._subscriptions_by_topic
            )
            self.direct_node = SimpleNamespace(
                get_name=lambda: "snapshot_direct",
                get_publishers_info_by_topic=self.get_publishers_info_by_topic,
                get_subscriptions_info_by_topic=self.get_subscriptions_info_by_topic,
            )
            self.daemon_node = SimpleNamespace(get_name=lambda: "snapshot_daemon")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(snapshot_module, "NodeStrategy", FakeNodeStrategy)
    monkeypatch.setattr(
        snapshot_module,
        "get_node_names",
        lambda node, include_hidden_nodes=True: [talker, listener],
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_action_server_info",
        lambda **kwargs: (
            [SimpleNamespace(name="/demo_action", types=["demo_msgs/action/Demo"])]
            if kwargs["remote_node_name"] == "/talker"
            else []
        ),
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_action_client_info",
        lambda **kwargs: (
            [SimpleNamespace(name="/demo_action", types=["demo_msgs/action/Demo"])]
            if kwargs["remote_node_name"] == "/listener"
            else []
        ),
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_publisher_info",
        lambda **kwargs: (
            [SimpleNamespace(name="/chatter", types=["std_msgs/msg/String"])]
            if kwargs["remote_node_name"] == "/talker"
            else []
        ),
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_subscriber_info",
        lambda **kwargs: (
            [SimpleNamespace(name="/chatter", types=["std_msgs/msg/String"])]
            if kwargs["remote_node_name"] == "/listener"
            else []
        ),
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_service_server_info",
        lambda **kwargs: (
            [SimpleNamespace(name="/demo_service", types=["std_srvs/srv/Empty"])]
            if kwargs["remote_node_name"] == "/talker"
            else []
        ),
    )
    monkeypatch.setattr(
        snapshot_module,
        "get_service_client_info",
        lambda **kwargs: (
            [SimpleNamespace(name="/demo_service", types=["std_srvs/srv/Empty"])]
            if kwargs["remote_node_name"] == "/listener"
            else []
        ),
    )
    monkeypatch.setattr(
        snapshot_module, "find_container_node_names", lambda **kwargs: []
    )

    ros_snapshot = snapshot_module.ROSSnapshot()

    patch_parameter_helpers(
        monkeypatch,
        ros_snapshot,
        {
            "/listener": {"queue_size": 10},
            "/talker": {"use_sim_time": True},
        },
    )
    monkeypatch.setattr(
        ros_snapshot,
        "_validate_and_update_models",
        lambda: None,
    )

    assert ros_snapshot.snapshot() is True

    deployment_model = ros_snapshot.ros_deployment_model
    assert set(deployment_model.node_bank.keys) == {"/talker", "/listener"}
    assert (
        deployment_model.topic_bank["/chatter"].construct_type == "std_msgs/msg/String"
    )
    assert set(deployment_model.action_bank["/demo_action"].client_node_names) == {
        "/listener"
    }
    assert set(deployment_model.action_bank["/demo_action"].server_node_names) == {
        "/talker"
    }
    assert deployment_model.service_bank["/demo_service"].construct_type == (
        "std_srvs/srv/Empty"
    )
    assert deployment_model.service_bank["/demo_service"].service_client_node_names == [
        "/listener"
    ]
    assert deployment_model.parameter_bank["/talker/use_sim_time"].value is True
    assert deployment_model.parameter_bank["/listener/queue_size"].value == 10


def test_main_happy_path_saves_requested_outputs(monkeypatch, tmp_path):
    reset_filters(monkeypatch)

    daemon_calls = []

    class RecordingModel:
        def __init__(self):
            self.calls = []

        def save_model_yaml_files(self, directory_path, base_file_name):
            self.calls.append(("yaml", directory_path, base_file_name))

        def save_model_json_files(self, directory_path, base_file_name):
            self.calls.append(("json", directory_path, base_file_name))

        def save_model_pickle_files(self, directory_path, base_file_name):
            self.calls.append(("pickle", directory_path, base_file_name))

        def save_model_info_files(self, directory_path, base_file_name):
            self.calls.append(("human", directory_path, base_file_name))

        def save_dot_graph_files(self, directory_path, base_file_name, show_graph=True):
            self.calls.append(("graph", directory_path, base_file_name, show_graph))

    class FakeSnapshot:
        def __init__(self, name):
            self.name = name
            self.specification_update = True
            self.ros_deployment_model = RecordingModel()
            self.ros_specification_model = RecordingModel()
            self.loaded_specs = []
            self.snapshot_calls = 0
            self.statistics_calls = 0
            self.unmatched_calls = 0

        def load_specifications(self, spec_path):
            self.loaded_specs.append(spec_path)
            return True

        def snapshot(self):
            self.snapshot_calls += 1
            return True

        def print_statistics(self):
            self.statistics_calls += 1

        def print_unmatched(self):
            self.unmatched_calls += 1

    fake_snapshot = FakeSnapshot("/snapshot_tool")

    monkeypatch.setattr(
        snapshot_module,
        "subprocess",
        SimpleNamespace(
            run=lambda *args, **kwargs: daemon_calls.append((args, kwargs)),
            DEVNULL=object(),
            CalledProcessError=RuntimeError,
        ),
    )
    monkeypatch.setattr(snapshot_module, "ROSSnapshot", lambda name: fake_snapshot)

    snapshot_module.main(
        [
            "--name",
            "/snapshot_tool",
            "--spec",
            str(tmp_path / "specs"),
            "--target",
            str(tmp_path / "output"),
            "--yaml",
            "yaml",
            "--json",
            "json",
            "--pickle",
            "pickle",
            "--human",
            "human",
            "--graph",
            "graphs",
            "--base",
            "snapshot",
            "--logger-threshold",
            "INFO",
        ]
    )

    output_root = os.path.expanduser(str(tmp_path / "output"))
    expected_deployment_calls = [
        ("yaml", os.path.join(output_root, "yaml"), "snapshot"),
        ("json", os.path.join(output_root, "json"), "snapshot"),
        ("pickle", os.path.join(output_root, "pickle"), "snapshot"),
        ("human", os.path.join(output_root, "human"), "snapshot"),
        ("graph", os.path.join(output_root, "graphs"), "snapshot", False),
    ]
    expected_spec_calls = [
        ("yaml", os.path.join(output_root, "yaml"), "snapshot"),
        ("json", os.path.join(output_root, "json"), "snapshot"),
        ("pickle", os.path.join(output_root, "pickle"), "snapshot"),
        ("human", os.path.join(output_root, "human"), "snapshot"),
    ]

    assert fake_snapshot.loaded_specs == [os.path.expanduser(str(tmp_path / "specs"))]
    assert fake_snapshot.snapshot_calls == 1
    assert fake_snapshot.statistics_calls == 1
    assert fake_snapshot.unmatched_calls == 1
    assert fake_snapshot.ros_deployment_model.calls == expected_deployment_calls
    assert fake_snapshot.ros_specification_model.calls == expected_spec_calls
    assert daemon_calls


def test_main_exits_when_specifications_fail_to_load(monkeypatch, tmp_path):
    reset_filters(monkeypatch)

    daemon_calls = []

    class FakeSnapshot:
        def __init__(self, name):
            self.name = name
            self.load_attempts = []
            self.snapshot_calls = 0

        def load_specifications(self, spec_path):
            self.load_attempts.append(spec_path)
            return False

        def snapshot(self):
            self.snapshot_calls += 1
            return True

    fake_snapshot = FakeSnapshot("/snapshot_tool")

    monkeypatch.setattr(
        snapshot_module,
        "subprocess",
        SimpleNamespace(
            run=lambda *args, **kwargs: daemon_calls.append((args, kwargs)),
            DEVNULL=object(),
            CalledProcessError=RuntimeError,
        ),
    )
    monkeypatch.setattr(snapshot_module, "ROSSnapshot", lambda name: fake_snapshot)

    with pytest.raises(SystemExit) as exc:
        snapshot_module.main(
            [
                "--name",
                "/snapshot_tool",
                "--spec",
                str(tmp_path / "specs"),
                "--target",
                str(tmp_path / "output"),
                "--yaml",
                "yaml",
                "--base",
                "snapshot",
                "--logger-threshold",
                "INFO",
            ]
        )

    assert exc.value.code == -1
    assert fake_snapshot.load_attempts == [os.path.expanduser(str(tmp_path / "specs"))]
    assert fake_snapshot.snapshot_calls == 0
    assert daemon_calls
