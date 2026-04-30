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

from pathlib import Path
from types import SimpleNamespace

from ros2_snapshot.core.specifications.node_specification import NodeSpecificationBank
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.core.specifications.type_specification import (
    TypeSpecificationBank,
    TypeSpecificationEnum,
)
from ros2_snapshot.workspace_modeler import (
    workspace_modeler as workspace_modeler_module,
)
from ros2_snapshot.workspace_modeler.workspace_modeler import PackageModeler


def make_package_modeler(installed_cache=None):
    package_modeler = object.__new__(PackageModeler)
    package_modeler._node_bank = NodeSpecificationBank()
    package_modeler._package_bank = PackageSpecificationBank()
    package_modeler._action_bank = TypeSpecificationBank()
    package_modeler._message_bank = TypeSpecificationBank()
    package_modeler._service_bank = TypeSpecificationBank()
    package_modeler._installed_deb_cache = installed_cache
    package_modeler._ros_model = None
    package_modeler._num = 0
    package_modeler._packages = None
    return package_modeler


def write_executable(path):
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)


def test_extract_type_specifications_collects_nested_spec_files(tmp_path):
    package_modeler = make_package_modeler()
    msg_dir = tmp_path / "msg"
    nested_dir = msg_dir / "nested"
    nested_dir.mkdir(parents=True)
    (msg_dir / "Foo.msg").write_text("string data\n", encoding="utf-8")
    (nested_dir / "Bar.msg").write_text("int32 count\n", encoding="utf-8")

    spec_names = package_modeler._extract_type_specifications(
        package_modeler.message_specification_bank,
        str(msg_dir),
        TypeSpecificationEnum.MSG,
        "demo_pkg",
        [],
    )

    assert set(spec_names) == {"Foo", "nested/Bar"}
    assert (
        package_modeler.message_specification_bank["demo_pkg/Foo"].construct_type
        == "msg"
    )
    assert (
        package_modeler.message_specification_bank["demo_pkg/Foo"].spec
        == "\nstring data\n"
    )
    assert package_modeler.message_specification_bank[
        "demo_pkg/nested/Bar"
    ].file_path == str(nested_dir / "Bar.msg")


def test_find_files_of_type_returns_nested_relative_paths(tmp_path):
    package_modeler = make_package_modeler()
    launch_dir = tmp_path / "launch"
    nested_dir = launch_dir / "nested"
    nested_dir.mkdir(parents=True)
    (launch_dir / "start.launch").write_text("<launch />\n", encoding="utf-8")
    (nested_dir / "debug.launch").write_text("<launch />\n", encoding="utf-8")

    launch_files = package_modeler._find_files_of_type(
        ".launch",
        str(launch_dir),
        "demo_pkg",
        "launch",
    )

    assert set(launch_files) == {"launch/start.launch", "launch/nested/debug.launch"}


def test_extract_type_specifications_avoids_symlink_cycles(tmp_path):
    package_modeler = make_package_modeler()
    msg_dir = tmp_path / "msg"
    msg_dir.mkdir()
    (msg_dir / "loop").symlink_to(Path("."))

    spec_names = package_modeler._extract_type_specifications(
        package_modeler.message_specification_bank,
        str(msg_dir),
        TypeSpecificationEnum.MSG,
        "demo_pkg",
        [],
    )

    assert spec_names == []


def test_find_files_of_type_avoids_symlink_cycles(tmp_path):
    package_modeler = make_package_modeler()
    launch_dir = tmp_path / "launch"
    launch_dir.mkdir()
    (launch_dir / "loop").symlink_to(Path("."))

    launch_files = package_modeler._find_files_of_type(
        ".launch",
        str(launch_dir),
        "demo_pkg",
        "launch",
    )

    assert launch_files == []


def test_collect_package_specs_collects_standard_share_content(tmp_path):
    package_modeler = make_package_modeler()
    share_path = tmp_path / "share" / "demo_pkg"
    (share_path / "msg" / "nested").mkdir(parents=True)
    (share_path / "srv").mkdir(parents=True)
    (share_path / "action").mkdir(parents=True)
    (share_path / "launch").mkdir(parents=True)
    (share_path / "config").mkdir(parents=True)
    (share_path / "scripts").mkdir(parents=True)

    (share_path / "msg" / "Foo.msg").write_text("string data\n", encoding="utf-8")
    (share_path / "msg" / "nested" / "Bar.msg").write_text(
        "int32 count\n", encoding="utf-8"
    )
    (share_path / "srv" / "DoThing.srv").write_text("---\n", encoding="utf-8")
    (share_path / "action" / "Run.action").write_text("---\n", encoding="utf-8")
    (share_path / "launch" / "start.launch").write_text(
        "<launch />\n", encoding="utf-8"
    )
    (share_path / "launch" / "start.xml").write_text("<launch />\n", encoding="utf-8")
    (share_path / "launch" / "launcher.py").write_text(
        "print('launch')\n", encoding="utf-8"
    )
    (share_path / "launch" / "params.yaml").write_text(
        "use_sim_time: true\n", encoding="utf-8"
    )
    (share_path / "config" / "demo.yaml").write_text("foo: bar\n", encoding="utf-8")
    (share_path / "config" / "extra.json").write_text("{}\n", encoding="utf-8")
    write_executable(share_path / "scripts" / "demo_node")

    package_spec = package_modeler.package_specification_bank["demo_pkg"]
    package_modeler._collect_package_specs("demo_pkg", str(share_path), package_spec)

    assert set(package_spec.messages) == {"Foo", "nested/Bar"}
    assert package_spec.services == ["DoThing"]
    assert package_spec.actions == ["Run"]
    assert set(package_spec.launch_files) == {
        "launch/start.launch",
        "launch/start.xml",
        "launch/launcher.py",
    }
    assert set(package_spec.parameter_files) == {
        "launch/params.yaml",
        "config/demo.yaml",
        "config/extra.json",
    }
    assert package_spec.nodes == ["demo_node"]
    assert (
        package_modeler.message_specification_bank["demo_pkg/Foo"].package == "demo_pkg"
    )
    assert (
        package_modeler.service_specification_bank["demo_pkg/DoThing"].construct_type
        == "srv"
    )
    assert (
        package_modeler.action_specification_bank["demo_pkg/Run"].construct_type
        == "action"
    )
    assert package_modeler.node_specification_bank[
        "demo_pkg/demo_node"
    ].file_path == str(share_path / "scripts" / "demo_node")


def test_get_installed_version_matches_dash_and_underscore_package_names():
    installed_cache = {
        "ros-rolling-demo-pkg": SimpleNamespace(
            installed=SimpleNamespace(version="1.2.3")
        )
    }
    package_modeler = make_package_modeler(installed_cache=installed_cache)

    assert package_modeler._get_installed_version("demo_pkg") == "1.2.3"
    assert (
        package_modeler._get_installed_version("missing_pkg") == "not installed in OS"
    )


def test_package_modeler_init_without_python_apt_keeps_os_version_lookup_optional(
    monkeypatch,
):
    monkeypatch.setattr(workspace_modeler_module, "apt", None)

    package_modeler = PackageModeler()

    assert package_modeler._installed_deb_cache is None


def test_collect_packages_walks_package_prefixes_and_collects_artifacts(
    monkeypatch, tmp_path
):
    prefix = tmp_path / "prefix"
    share_path = prefix / "share" / "demo_pkg"
    lib_path = prefix / "lib" / "demo_pkg"
    (share_path / "msg").mkdir(parents=True)
    lib_path.mkdir(parents=True)

    (share_path / "package.xml").write_text(
        """
        <package format="2">
          <name>demo_pkg</name>
          <version>1.0.0</version>
          <description>demo</description>
          <maintainer email="demo@example.com">Demo</maintainer>
          <license>Apache-2.0</license>
          <depend>rclpy</depend>
          <exec_depend>std_msgs</exec_depend>
        </package>
        """.strip(),
        encoding="utf-8",
    )
    (share_path / "msg" / "Foo.msg").write_text("string data\n", encoding="utf-8")
    write_executable(lib_path / "demo_node")

    monkeypatch.setattr(
        workspace_modeler_module,
        "get_packages_with_prefixes",
        lambda: {"demo_pkg": str(prefix)},
    )

    package_modeler = make_package_modeler(installed_cache={})
    package_modeler._collect_packages()

    package_spec = package_modeler.package_specification_bank["demo_pkg"]
    node_spec = package_modeler.node_specification_bank["demo_pkg/demo_node"]

    assert package_modeler._num == 1
    assert package_spec.share_path == str(share_path)
    assert package_spec.package_version == "1.0.0"
    assert set(package_spec.dependencies) == {"rclpy", "std_msgs"}
    assert package_spec.messages == ["Foo"]
    assert package_spec.nodes == ["demo_node"]
    assert node_spec.package == "demo_pkg"
    assert node_spec.file_path == str(lib_path / "demo_node")


def test_collect_packages_skips_packages_with_missing_paths(monkeypatch, tmp_path):
    package_modeler = make_package_modeler(installed_cache={})
    package_spec = package_modeler.package_specification_bank["demo_pkg"]
    package_spec.share_path = str(tmp_path / "missing_share")

    monkeypatch.setattr(
        workspace_modeler_module,
        "get_packages_with_prefixes",
        lambda: {"demo_pkg": str(tmp_path / "prefix")},
    )
    monkeypatch.setattr(
        package_modeler,
        "_share_instance",
        lambda _pkg_name, _pkg_path: package_spec,
    )

    package_modeler._collect_packages()

    assert package_modeler._num == 1
    assert package_modeler.node_specification_bank.keys == []


def test_share_instance_records_package_version_without_os_package_lookup(tmp_path):
    share_path = tmp_path / "prefix" / "share" / "demo_pkg"
    share_path.mkdir(parents=True)
    (share_path / "package.xml").write_text(
        """
        <package format="2">
          <name>demo_pkg</name>
          <version>2.3.4</version>
          <description>demo</description>
          <maintainer email="demo@example.com">Demo</maintainer>
          <license>Apache-2.0</license>
        </package>
        """.strip(),
        encoding="utf-8",
    )

    package_modeler = make_package_modeler(installed_cache=None)
    package_spec = package_modeler._share_instance("demo_pkg", str(tmp_path / "prefix"))

    assert package_spec is not None
    assert package_spec.package_version == "2.3.4"
    assert package_spec.installed_version is None
