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

"""Metamodels used to model ROS Message, Action, Service Specifications and the Banks that contain them."""

from enum import Enum, unique
from typing import Any, ClassVar, Optional

from core.base_metamodel import _BankMetamodel, _EntityMetamodel


@unique
class TypeSpecificationEnum(Enum):
    """Enumerated type for SpecificationBuilder identifiers."""

    MSG = 1
    ACTION = 2
    SRV = 3


class TypeSpecification(_EntityMetamodel):
    """Metamodel for ROS Message, Action, or Service Specifications."""

    yaml_tag: ClassVar[str] = "!TypeSpecification"

    construct_type: Optional[str] = None
    file_path: Optional[str] = None
    package: Optional[str] = None
    spec: Optional[Any] = None

    def __init__(self, **kwargs):
        """Initialize instance of TypeSpecification."""
        super().__init__(**kwargs)
        self.construct_type = kwargs.get("construct_type", None)
        self.file_path = kwargs.get("file_path", None)
        self.package = kwargs.get("package", None)
        self.spec = kwargs.get("spec", None)


class TypeSpecificationBank(_BankMetamodel):
    """Metamodel for Bank of ROS Message, Service, or Action Specifications."""

    yaml_tag: ClassVar[str] = "!TypeSpecBank"
    HUMAN_OUTPUT_NAME: ClassVar[str] = "TypeSpecifications:"

    def __init__(self, **kwargs):
        """Initialize instance of TypeSpecificationBank."""
        return super().__init__(**kwargs)

    def _create_entity(self, name):
        """
        Create instance of named entity given bank type.

        :return: instance of entity
        """
        return TypeSpecification(name=name)

    def entity_class(self, name):
        """
        Return class of entity given bank type.

        :return: instance of entity class definition
        """
        return TypeSpecification
