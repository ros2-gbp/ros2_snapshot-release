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

"""Metamodels used to model ROS Packages and the Banks that contain them."""

from typing import ClassVar, List, Optional

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


class PackageSpecification(_EntityMetamodel):
    """Metamodel for ROS Package specifications."""

    yaml_tag: ClassVar[str] = "!PackageSpecification"

    actions: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    installed_version: Optional[str] = None
    is_metapackage: bool = False
    launch_files: Optional[List[str]] = None
    messages: Optional[List[str]] = None
    nodes: Optional[List[str]] = None
    package_version: Optional[str] = None
    parameter_files: Optional[List[str]] = None
    services: Optional[List[str]] = None
    share_path: Optional[str] = None

    def __init__(self, **kwargs):
        """Initialize PackageSpecification."""
        super().__init__(**kwargs)
        self.actions = kwargs.get("actions", None)
        self.dependencies = kwargs.get("dependencies", None)
        self.installed_version = kwargs.get("installed_version", None)
        self.is_metapackage = kwargs.get("is_metapackage", False)
        self.launch_files = kwargs.get("launch_files", None)
        self.messages = kwargs.get("messages", None)
        self.nodes = kwargs.get("nodes", None)
        self.package_version = kwargs.get("package_version", None)
        self.parameter_files = kwargs.get("parameter_files", None)
        self.services = kwargs.get("services", None)
        self.share_path = kwargs.get("share_path", None)


class PackageSpecificationBank(_BankMetamodel):
    """Metamodel for Bank of ROS Package specifications."""

    yaml_tag: ClassVar[str] = "!PackageSpecBank"
    HUMAN_OUTPUT_NAME: ClassVar[str] = "PackageSpecifications:"

    def __init__(self, **kwargs):
        """Initialize PackageSpecificationBank."""
        super().__init__(**kwargs)

    def _create_entity(self, name):
        """
        Create instance of named entity given bank type.

        :return: instance of entity
        """
        return PackageSpecification(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return PackageSpecification
