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

"""
Workspace_modeler: a tool for probing ROS installation and workspace.

This discovers all ROS packages and documents the configuruation.
"""

import argparse
import os
import stat
import sys
import time
import xml.etree.ElementTree as ET

from ament_index_python import get_packages_with_prefixes
from ament_index_python.packages import get_package_share_directory

import apt

from core.ros_model import BankType, ROSModel
from core.specifications.node_specification import NodeSpecificationBank
from core.specifications.package_specification import (
    PackageSpecificationBank,
)
from core.specifications.type_specification import (
    TypeSpecificationBank,
    TypeSpecificationEnum,
)
from core.utilities.logger import Logger, LoggerLevel

# Any executable file permission
# stat.S_IEXEC: This flag represents the executable permission for the file's owner.
# stat.S_IXGRP: This flag represents the executable permission for the group.
# stat.S_IXOTH: This flag represents the executable permission for others (everyone else).
executable_flags = stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH


class PackageModeler(object):
    """Class responsible for crawling ROS workspace and extracting package information."""

    source_name = "package_modeler"

    def __init__(self):
        """Instantiate an instance of the PackageModeler."""
        self._package_bank = PackageSpecificationBank()
        self._node_bank = NodeSpecificationBank()
        self._action_bank = TypeSpecificationBank()
        self._message_bank = TypeSpecificationBank()
        self._service_bank = TypeSpecificationBank()
        self._ros_model = None
        self._num = 0
        self._packages = None

        self._installed_deb_cache = None

        try:
            cache = apt.Cache()
            self._installed_deb_cache = {
                pkg.name: pkg for pkg in cache if pkg.is_installed
            }
        except Exception as exc:  # noqa: B902
            print(exc)

    @property
    def node_specification_bank(self):
        """
        Return the NodeBankBuilder.

        :return: the NodeBankBuilder
        :rtype: NodeBankBuilder
        """
        return self._node_bank

    @property
    def message_specification_bank(self):
        """
        Return the SpecificationBankBuilder for Message Specifications.

        :return: the SpecificationBankBuilder for Message Specifications
        :rtype: SpecificationBankBuilder
        """
        return self._message_bank

    @property
    def service_specification_bank(self):
        """
        Return the SpecificationBankBuilder for Service Specifications.

        :return: the SpecificationBankBuilder for Service Specifications
        :rtype: SpecificationBankBuilder
        """
        return self._service_bank

    @property
    def action_specification_bank(self):
        """
        Return the SpecificationBankBuilder for Action Specifications.

        :return: the SpecificationBankBuilder for Action Specifications
        :rtype: SpecificationBankBuilderpackage_name
        """
        return self._action_bank

    @property
    def package_specification_bank(self):
        """
        Return the PackageBankBuilder.

        :return: the PackageBankBuilder
        :rtype: PackageBankBuilder
        """
        return self._package_bank

    @property
    def ros_model(self):
        """
        Return the snapshotModel instance.

        :return: the snapshotModel instance, if called after the probe
            method; Otherwise, None
        :rtype: snapshotModel
        """
        return self._ros_model

    def crawl(self):
        """
        Crawl the ROS workspace to populate the snapshotModel with the details of the ROS Packages in workspace.

        :return: True if successful; False if failures were encountered
        :rtype: bool
        """
        try:
            Logger.get_logger().log(LoggerLevel.INFO, "Collect package information ...")
            self._collect_packages()
            Logger.get_logger().log(
                LoggerLevel.INFO,
                f"Found {len(self.package_specification_bank.keys)} packages on system ...",
            )

            Logger.get_logger().log(
                LoggerLevel.INFO,
                "Preparing snapshotModel instances ...",
            )

            self._ros_model = ROSModel(
                {
                    BankType.PACKAGE_SPECIFICATION: self._package_bank,
                    BankType.NODE_SPECIFICATION: self._node_bank,
                    BankType.ACTION_SPECIFICATION: self._action_bank,
                    BankType.MESSAGE_SPECIFICATION: self._message_bank,
                    BankType.SERVICE_SPECIFICATION: self._service_bank,
                }
            )
            return True
        except Exception as exc:  # noqa: B902
            Logger.get_logger().log(
                LoggerLevel.ERROR,
                f"Failed to gather ROS package information!:\n"
                f"      {type(exc)} - {exc}",
            )
            return False

    def _share_instance(self, pkg_name, pkg_path):
        """Find required package.xml in share folder and get dependencies."""
        share_path = os.path.join(pkg_path, "share", pkg_name)
        try:
            path = os.path.join(share_path, "package.xml")
            if not os.path.exists(path):
                return None
            package_dependencies = []
            try:

                tree = ET.parse(path)
                root = tree.getroot()
                for depend_type in (
                    "depend",
                    "build_depend",
                    "build_export_depend",
                    "exec_depend",
                ):
                    try:
                        for dependency in root.findall(depend_type):
                            package_dependencies.append(dependency.text)
                    except Exception:  # noqa: B902
                        print(
                            f"\x1b[91mDid not find '{depend_type}' in package definition!\x1b[0m",
                            flush=True,
                        )

                installed_version = self._get_installed_version(pkg_name)
                package = self._package_bank[os.path.basename(pkg_name)]
                package.update_attributes(
                    share_path=share_path,
                    dependencies=package_dependencies,
                    source=PackageModeler.source_name,
                    installed_version=installed_version,
                )
                return package
            except ValueError as exc:
                print(
                    f"\x1b[91mUnknown share path for '{pkg_name}' "
                    f"at '{share_path} - skip this package!\n    {type(exc)} {exc}\x1b[0m",
                    flush=True,
                )
                return None
        except Exception as exc:  # noqa: B902
            raise exc

    def _lib_instance(self, pkg_name, pkg_path):
        """Find executable files in package lib folder."""
        # Ignoring anything under 'lib/python.../pkg_name' presuming entry point defined
        lib_path = os.path.join(pkg_path, "lib", pkg_name)

        if not os.path.exists(lib_path):
            return

        try:
            node_names = self._find_executable_files(
                os.path.basename(lib_path), lib_path, pkg_name
            )
            if len(node_names) > 0:
                self._package_bank[pkg_name].update_attributes(nodes=node_names)
        except Exception as exc:  # noqa: B902
            print(
                f"\x1b[91mError searching library path for '{pkg_name}' "
                f"at '{lib_path}!\n    {type(exc)} {exc}\x1b[0m",
                flush=True,
            )

    def _collect_packages(self):
        """Collect package specifications into dictionary of packages."""
        ros_packages = get_packages_with_prefixes()

        data_counts = {
            "nodes": 0,
            "messages": 0,
            "services": 0,
            "actions": 0,
            "launch_files": 0,
            "parameter_files": 0,
        }

        for pkg_name, pkg_path in ros_packages.items():

            pkg_data = self._share_instance(pkg_name, pkg_path)
            if pkg_data is not None:
                self._num += 1

                # Get executable data and parameters from lib path
                self._lib_instance(pkg_name, pkg_path)

                # Get package specs from share folder
                self._collect_package_specs(
                    pkg_name, pkg_data.share_path, pkg_data, None
                )
                for key, value in data_counts.items():
                    if isinstance(getattr(pkg_data, key), list):
                        cnt = len(getattr(pkg_data, key))
                        data_counts[key] += cnt

    def _get_installed_version(self, pkg_name):
        """Get the installed version of package."""
        if self._installed_deb_cache is None:
            return None

        for key in self._installed_deb_cache:
            if key.endswith(pkg_name):
                return self._installed_deb_cache[key].installed.version

            # ROS packages use - instead of _, so check those as well
            if key.endswith(pkg_name.replace("_", "-")):
                return self._installed_deb_cache[key].installed.version

        return "not installed in OS"

    def _find_executable_files(self, child_name, full_path, pkg_name, link_path=None):
        """
        Look in this and sub-folders for executable files.

        :param child_name: child of parent directory
        :param full_path: path to current file or directory
        :param pkg_name: where we are looking
        :return : List of strings as potential nodes.
        """
        more_node_names = []
        if os.path.islink(full_path):
            new_path = os.readlink(full_path)

            more_node_names.extend(
                self._find_executable_files(child_name, new_path, pkg_name, full_path)
            )
        elif os.path.isfile(full_path):
            status = os.stat(full_path)
            mode = status.st_mode
            if mode & executable_flags:
                self._update_node_data(pkg_name, more_node_names, full_path, link_path)
            # else:
            #    file_path_base, file_ext = os.path.splitext(full_path)
            #    file_base = os.path.basename(file_path_base)

        elif os.path.isdir(full_path):
            for child_name in os.listdir(full_path):
                if child_name in ("__pycache__", "hook") or "egg-info" in child_name:
                    # Skip some standard subfolders
                    continue
                new_path = os.path.join(full_path, child_name)
                more_nodes = self._find_executable_files(
                    child_name, new_path, pkg_name, link_path
                )
                more_node_names.extend(more_nodes)

        return more_node_names

    def _update_node_data(self, pkg_name, more_node_names, full_path, link_path):
        """
        Update node data given a found executable file.

        At this point, we assume any executable files is a ROS node, but it is not marked as validated.
        """
        file_path_base, _ = os.path.splitext(full_path)
        file_base = os.path.basename(file_path_base)
        more_node_names.append(file_base)  # add to list of nodes

        # Store node name with package to ensure uniqueness
        ref_name = "/".join([pkg_name, file_base])

        file_path = full_path

        if ref_name in self._node_bank:
            print(
                f"\x1b[91m        Discovered duplicate node '{ref_name}' "
                f"- overwriting data for now!\x1b[0m",
                flush=True,
            )

        node = self._node_bank[full_path]
        node.update_attributes(
            package=pkg_name,
            file_path=file_path,
            source=PackageModeler.source_name,
        )

    def _collect_package_specs(self, pkg_name, search_path, pkg_data, link_path=None):
        """
        Process each package to extract specifications.

        : pkg_name - package name
        : pkg_data - package meta data instance
        : return None
        """
        try:
            for child_name in os.listdir(search_path):
                if child_name in (
                    "cmake",
                    "environment",
                    "hook",
                    "local_setup.bash",
                    "local_setup.dsv",
                    "local_setup.sh",
                    "local_setup.zsh",
                    "package.dsv",
                    "package.xml",
                ):
                    continue
                full_path = os.path.join(search_path, child_name)
                if os.path.islink(full_path):
                    link_path = os.readlink(full_path)
                    self._collect_package_specs(
                        pkg_name, link_path, pkg_data, full_path
                    )

                elif os.path.isfile(full_path):
                    if child_name in [
                        "package.xml",
                        "CMakeLists.txt",
                        "setup.cfg",
                        "setup.py",
                        "README.md",
                        "CHANGELOG.rst",
                    ]:
                        pass
                    else:
                        # Might be an executable file, so assume node for now
                        status = os.stat(full_path)
                        mode = status.st_mode
                        if mode & executable_flags:
                            more_node_names = []
                            self._update_node_data(
                                pkg_name, more_node_names, full_path, link_path
                            )
                            pkg_data.update_attributes(nodes=more_node_names)
                elif os.path.isdir(full_path):
                    # search standard sub-folders for specifications
                    if child_name == "action":
                        new_actions = self._extract_type_specifications(
                            self._action_bank,
                            full_path,
                            TypeSpecificationEnum.ACTION,
                            pkg_name,
                            [],
                        )
                        pkg_data.update_attributes(actions=new_actions)
                    elif child_name == "msg":
                        new_messages = self._extract_type_specifications(
                            self._message_bank,
                            full_path,
                            TypeSpecificationEnum.MSG,
                            pkg_name,
                            [],
                        )
                        pkg_data.update_attributes(messages=new_messages)
                    elif child_name == "srv":
                        new_services = self._extract_type_specifications(
                            self._service_bank,
                            full_path,
                            TypeSpecificationEnum.SRV,
                            pkg_name,
                            [],
                        )
                        pkg_data.update_attributes(services=new_services)
                    elif child_name == "launch":
                        new_launches = self._find_files_of_type(
                            ".launch", full_path, pkg_name, child_name
                        )
                        pkg_data.update_attributes(launch_files=new_launches)

                        new_launches = self._find_files_of_type(
                            ".xml", full_path, pkg_name, child_name
                        )
                        pkg_data.update_attributes(launch_files=new_launches)

                        new_launches = self._find_files_of_type(
                            ".py", full_path, pkg_name, child_name
                        )
                        pkg_data.update_attributes(launch_files=new_launches)

                        new_params = self._find_files_of_type(
                            ".yaml", full_path, pkg_name, child_name
                        )
                        pkg_data.update_attributes(parameter_files=new_params)

                    elif child_name in ("cfg", "config", "param", "yaml"):
                        # General form of possible param folders (consider expansive possibilities)
                        for ext in (".cfg", ".csv", ".json", ".txt", ".xml", ".yaml"):
                            new_params = self._find_files_of_type(
                                ext, full_path, pkg_name, child_name
                            )
                            pkg_data.update_attributes(parameter_files=new_params)
                    elif child_name == "bin" or child_name == "scripts":
                        more_nodes = self._find_executable_files(
                            child_name, full_path, pkg_name, link_path
                        )
                        pkg_data.update_attributes(nodes=more_nodes)
                    else:
                        # some other folder - keep going deeper
                        if child_name in ("hook"):
                            print(
                                f"        skipping '{child_name}' from '{full_path}'",
                                flush=True,
                            )
                        else:
                            self._collect_package_specs(
                                pkg_name, full_path, pkg_data, link_path
                            )

        except NotADirectoryError:
            pass  # expected error
        except Exception as exc:  # noqa: B902
            print(f"Error collecting package specs!\n    {exc}")
            raise exc

    def _extract_type_specifications(
        self, spec_bank, full_path, spec_type, pkg_name, base_name
    ):
        """Extract a specification for action, message, or services given path and type."""
        spec_names = []

        spec_ext = f".{spec_type.name.lower()}"

        for child_name in os.listdir(full_path):
            child_path = os.path.join(full_path, child_name)
            if os.path.isfile(child_path):
                file_base, file_ext = os.path.splitext(child_name)

                if file_ext == spec_ext:
                    try:
                        with open(child_path, "r") as fin:
                            # prepend newline for output formatting in yaml
                            spec_text = "\n" + fin.read()

                            # Include base_name for sub folder processing
                            ref_name = "/".join(base_name + [file_base])
                            spec_names.append(
                                ref_name
                            )  # add to list of specs per package

                            # Store specification name with package to ensure uniqueness
                            ref_name = "/".join(
                                [os.path.basename(pkg_name)] + [ref_name]
                            )
                            spec = spec_bank[ref_name]
                            spec.update_attributes(
                                construct_type=spec_ext[1:],
                                package=os.path.basename(pkg_name),
                                file_path=child_path,
                                spec=spec_text,
                                source=PackageModeler.source_name,
                            )
                    except IOError as ex:
                        print(" IOError reading spec:", type(ex), ex)
                        print("   ", child_path)
                    except Exception as ex:  # noqa: B902
                        print(" Unknown error reading spec:", type(ex), ex)
                        print("   ", child_path)
                        raise ex

            elif os.path.isdir(child_path):
                # Recurse into sub-folders to see if sub-specifications are defined
                sub_specs = self._extract_type_specifications(
                    spec_bank,
                    child_path,
                    spec_type,
                    pkg_name,
                    base_name + [child_name],
                )
                spec_names.extend(sub_specs)

        return spec_names

    def _find_files_of_type(self, target_ext, full_path, pkg_name, sub_folder=""):
        """Find all files of given type in folder."""
        file_names = []
        for child_name in os.listdir(full_path):
            child_path = os.path.join(full_path, child_name)
            if os.path.isfile(child_path):
                if child_name.endswith(target_ext):
                    file_names.append(os.path.join(sub_folder, child_name))
            elif os.path.isdir(child_path):
                sub_file_names = self._find_files_of_type(
                    target_ext,
                    child_path,
                    pkg_name,
                    sub_folder=os.path.join(sub_folder, child_name),
                )
                file_names.extend(sub_file_names)

        return file_names

    def print_statistics(self):
        """Print statistics."""
        print("------ Specifications ------")
        for bank_type in ROSModel.SPECIFICATION_TYPES:
            bank = self.ros_model[bank_type]
            print(
                f"     {len(bank.keys):4d}  items in {ROSModel.BANK_TYPES_TO_OUTPUT_NAMES[bank_type]}",
                flush=True,
            )


def get_options(argv):
    """
    Get command line options for package modeler.

    :param argv: command line arguments
    """
    parser = argparse.ArgumentParser(
        usage="ros2 run ros2_snapshot workspace [options]",
        description="""
        Probe ROS workspace to retrieve a model of available ROS components,
        then create a model using snapshot_modeling metamodels.

        By default, YAML and pickle files are stored.
        """.strip(),
    )

    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        default="~/.snapshot_modeling",
        type=str,
        action="store",
        help="target output directory (default='~/.snapshot_modeling')",
    )
    parser.add_argument(
        "-r",
        "--human",
        dest="human",
        default=None,
        type=str,
        action="store",
        help="output human readable text format to directory (default=None)",
    )
    parser.add_argument(
        "-y",
        "--yaml",
        dest="yaml",
        default="yaml",
        type=str,
        action="store",
        help="output yaml format to directory (default='yaml')",
    )
    parser.add_argument(
        "-j",
        "--json",
        dest="json",
        default=None,
        type=str,
        action="store",
        help="output json format to directory (default=None)",
    )
    parser.add_argument(
        "-p",
        "--pickle",
        dest="pickle",
        default="pickle",
        type=str,
        action="store",
        help="output pickle format to directory (default='pickle')",
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all",
        default=False,
        action="store_true",
        help="output all possible formats",
    )
    parser.add_argument(
        "-b",
        "--base",
        dest="base",
        default="snapshot",
        type=str,
        action="store",
        help="output base file name (default='snapshot')",
    )
    parser.add_argument(
        "-v",
        "--version",
        dest="version",
        default=False,
        action="store_true",
        help="display version information",
    )
    parser.add_argument(
        "-lt",
        "--logger_threshold",
        dest="logger_threshold",
        choices={
            "ERROR": LoggerLevel.ERROR,
            "WARNING": LoggerLevel.WARNING,
            "INFO": LoggerLevel.INFO,
            "DEBUG": LoggerLevel.DEBUG,
        },
        default="INFO",
        help="logger threshold (default='INFO')",
    )

    options, _ = parser.parse_known_args(argv)

    if options.all:
        if options.human is None:
            options.human = "human"
        if options.yaml is None:
            options.yaml = "yaml"
        if options.json is None:
            options.json = "json"
        if options.pickle is None:
            options.pickle = "pickle"

    if not any((options.yaml, options.json, options.human, options.pickle)):
        # Verify that at least one output is selected, otherwise not point in running
        Logger.get_logger().log(LoggerLevel.ERROR, "Model Loader usage error!")
        print(
            "\x1b[91m    At least one output type must be specified (or --all)!\n\x1b[96m"
        )
        parser.print_help()
        print("================================\x1b[0m", flush=True)
        sys.exit(-1)

    if options.version:
        print(parser.usage)
        try:
            from importlib.metadata import version

            print(
                f"ros2_snapshot:workspace_modeler v{version('ros2_snapshot')}",
                flush=True,
            )
        except Exception:  # noqa: B902
            try:
                share_dir = get_package_share_directory("ros2_snapshot")
                file_name = os.path.join(share_dir, "VERSION")
                with open(file_name) as fin:
                    v = fin.read().strip()
                print(f"ros2_snapshot:workspace_modeler v{v}", flush=True)
            except Exception:  # noqa: B902
                print("Unknown version", flush=True)
        sys.exit(0)

    return options


def main(argv=None):
    """
    Run the method for the ROS Snapshot tool.

    This is the driver that sets up and runs everything.
    """
    options = get_options(argv)

    Logger.LEVEL = options.logger_threshold
    Logger.get_logger().log(LoggerLevel.INFO, "Initializing workspace modeler...")

    start_time = time.time()
    modeler = PackageModeler()
    if modeler.crawl():
        Logger.get_logger().log(
            LoggerLevel.INFO,
            f"Saving workspace modeler output to '{options.target}' ...",
        )
        if options.yaml is not None:
            modeler.ros_model.save_model_yaml_files(
                os.path.join(options.target, options.yaml), options.base
            )

        if options.json is not None:
            modeler.ros_model.save_model_json_files(
                os.path.join(options.target, options.json), options.base
            )

        if options.pickle is not None:
            modeler.ros_model.save_model_pickle_files(
                os.path.join(options.target, options.pickle), options.base
            )

        if options.human is not None:
            modeler.ros_model.save_model_info_files(
                os.path.join(options.target, options.human), options.base
            )

        Logger.get_logger().log(
            LoggerLevel.INFO,
            f"Finished workspace modeling in {time.time() - start_time:.3f} seconds",
        )
        modeler.print_statistics()

    else:
        Logger.get_logger().log(
            LoggerLevel.ERROR, "Failed to extract specifications for ROS workspace ..."
        )


if __name__ == "__main__":
    main(sys.argv)
