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

import importlib.metadata

import pytest

from ros2_snapshot.snapshot import snapshot as snapshot_module
from ros2_snapshot.workspace_modeler import workspace_modeler as workspace_module


def test_snapshot_get_options_all_enables_all_outputs():
    options = snapshot_module.get_options(
        ["--all", "--name", "/cli_snapshot", "--target", "/tmp/out"]
    )

    assert options.human == "human"
    assert options.json == "json"
    assert options.yaml == "yaml"
    assert options.pickle == "pickle"
    assert options.graph == "dot_graph"
    assert options.name == "/cli_snapshot"
    assert options.target == "/tmp/out"


def test_workspace_get_options_all_enables_all_outputs():
    options = workspace_module.get_options(["--all", "--target", "/tmp/out"])

    assert options.human == "human"
    assert options.json == "json"
    assert options.yaml == "yaml"
    assert options.pickle == "pickle"
    assert options.target == "/tmp/out"


@pytest.mark.parametrize(
    ("get_options", "prefix"),
    [
        (snapshot_module.get_options, "ros2_snapshot:snapshot"),
        (workspace_module.get_options, "ros2_snapshot:workspace_modeler"),
    ],
)
def test_cli_version_option_exits_successfully(
    monkeypatch, capsys, get_options, prefix
):
    monkeypatch.setattr(importlib.metadata, "version", lambda package_name: "9.9.9")

    with pytest.raises(SystemExit) as exc:
        get_options(["--version"])

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert prefix in captured.out
    assert "9.9.9" in captured.out


def test_workspace_main_happy_path_saves_requested_outputs(monkeypatch, tmp_path):
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

    class FakeModeler:
        def __init__(self):
            self.ros_model = RecordingModel()
            self.crawl_calls = 0
            self.statistics_calls = 0

        def crawl(self):
            self.crawl_calls += 1
            return True

        def print_statistics(self):
            self.statistics_calls += 1

    fake_modeler = FakeModeler()

    monkeypatch.setattr(workspace_module, "PackageModeler", lambda: fake_modeler)

    workspace_module.main(
        [
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
            "--base",
            "snapshot",
            "--logger-threshold",
            "INFO",
        ]
    )

    assert fake_modeler.crawl_calls == 1
    assert fake_modeler.statistics_calls == 1
    assert fake_modeler.ros_model.calls == [
        ("yaml", str(tmp_path / "output" / "yaml"), "snapshot"),
        ("json", str(tmp_path / "output" / "json"), "snapshot"),
        ("pickle", str(tmp_path / "output" / "pickle"), "snapshot"),
        ("human", str(tmp_path / "output" / "human"), "snapshot"),
    ]


def test_workspace_main_does_not_save_outputs_when_crawl_fails(monkeypatch, tmp_path):
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

    class FakeModeler:
        def __init__(self):
            self.ros_model = RecordingModel()
            self.crawl_calls = 0
            self.statistics_calls = 0

        def crawl(self):
            self.crawl_calls += 1
            return False

        def print_statistics(self):
            self.statistics_calls += 1

    fake_modeler = FakeModeler()

    monkeypatch.setattr(workspace_module, "PackageModeler", lambda: fake_modeler)

    workspace_module.main(
        [
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
            "--base",
            "snapshot",
            "--logger-threshold",
            "INFO",
        ]
    )

    assert fake_modeler.crawl_calls == 1
    assert fake_modeler.statistics_calls == 0
    assert fake_modeler.ros_model.calls == []
