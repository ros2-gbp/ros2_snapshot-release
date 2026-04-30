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

"""Base Metamodels used to model ROS Entities and the Banks that contain them."""

import inspect
import traceback
import warnings
from typing import Any, ClassVar, Dict, Optional, Union, get_args, get_origin

from ros2_snapshot.core.utilities.logger import Logger, LoggerLevel


def _type_includes_set(tp):
    """Return True if tp or any of its type arguments is a Set type."""
    if get_origin(tp) is set:
        return True
    return any(_type_includes_set(a) for a in get_args(tp))


def _iter_model_subclasses(model_class):
    """Yield all subclasses of model_class, including indirect subclasses."""
    for subclass in model_class.__subclasses__():
        yield subclass
        yield from _iter_model_subclasses(subclass)


try:
    from pydantic.v1 import BaseModel, ValidationError, root_validator

    def _pre_root_validator(fn):
        return root_validator(pre=True)(fn)

except ImportError:
    from pydantic import BaseModel, ValidationError

    try:
        from pydantic import root_validator

        def _pre_root_validator(fn):
            return root_validator(pre=True)(fn)

    except ImportError:
        from pydantic import model_validator

        def _pre_root_validator(fn):
            return model_validator(mode="before")(classmethod(fn))


class _EntityMetamodel(BaseModel):
    """Internal Base Metamodel for ROS Entities."""

    yaml_tag: ClassVar[str] = ""
    _tag_to_class: ClassVar[Optional[Dict[str, type]]] = None
    _name_to_class: ClassVar[Optional[Dict[str, type]]] = None

    name: Optional[str] = None
    source: Optional[str] = None
    version: int = 0

    def __init_subclass__(cls, **kwargs):
        """Invalidate lookup caches when new entity metamodel classes load."""
        super().__init_subclass__(**kwargs)
        _EntityMetamodel._tag_to_class = None
        _EntityMetamodel._name_to_class = None

    def __init__(self, **kwargs):
        """
        Create a new instance of the ROS Entity Metamodel.

        This uses keyword arguments (for the purposes of loading from YAML)

        :param kwargs: the keyword arguments to create a new
            ROS Entity Metamodel from
        :type kwargs: dict{str: value}
        """
        super().__init__(**kwargs)
        for key in kwargs:
            self.__setattr__(key, kwargs[key])

    def __contains__(self, key):
        """Check if instance contains the specified attribute."""
        return key in self.__dict__

    def update_attributes(self, **kwargs):
        """
        Update attributes for entity.

        :param kwargs: the keyword arguments to create a new
            ROS Entity Metamodel from
        :type kwargs: dict{str: value}
        """
        for key in kwargs:
            try:
                val = self.__getattribute__(key)
            except AttributeError:
                # Just means we are adding a new attribute
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    f"Adding new attribute '{key}' to '{self.name}' ({self.__class__.__name__}).",
                )
                self.__setattr__(key, kwargs[key])
                continue

            # Handle updating an existing attribute
            if val is None:
                self.__setattr__(key, kwargs[key])

            else:
                if val == kwargs[key] and key != "version":
                    # No need to update if same value
                    # unless version, where we increment if updating
                    continue
                elif kwargs[key] is None:
                    # No need to update if None data provided
                    continue
                elif key == "version":
                    if isinstance(val, int):
                        # Increment integer type
                        try:
                            val2 = int(kwargs[key])
                            val = max(val, val2)
                        except (KeyError, TypeError):
                            pass
                        except Exception as ex:  # noqa: B902
                            Logger.get_logger().log(
                                LoggerLevel.WARNING,
                                f"Failed to update version field '{key}' on {self.__class__.__name__}: "
                                f"{ex}\n{traceback.format_exc()}",
                            )
                        self.__setattr__(key, val + 1)
                    else:
                        val = str(val) + "_" + str(kwargs[key])
                        self.__setattr__(key, val)
                else:
                    # Update based on specific types
                    if isinstance(val, list):
                        if isinstance(kwargs[key], list):
                            val.extend(kwargs[key])
                        else:
                            if kwargs[key] not in val:
                                val.append(kwargs[key])
                    elif isinstance(val, dict):
                        val.update(kwargs[key])
                    elif isinstance(val, set):
                        val.update(kwargs[key])
                    elif isinstance(val, str):
                        fields = getattr(self, "__fields__", {})
                        field = fields.get(key)
                        use_set = field is not None and _type_includes_set(
                            field.outer_type_
                        )
                        if use_set:
                            new_coll = {val}
                            if isinstance(kwargs[key], (set, list)):
                                new_coll.update(kwargs[key])
                            else:
                                new_coll.add(kwargs[key])
                        else:
                            new_coll = [val]
                            if isinstance(kwargs[key], list):
                                new_coll.extend(kwargs[key])
                            else:
                                if kwargs[key] not in new_coll:
                                    new_coll.append(kwargs[key])
                        self.__setattr__(key, new_coll)
                    else:
                        # By default just update the attribute
                        self.__setattr__(key, kwargs[key])

    def add_to_dot_graph(self, graph):
        """
        Add the ROS Entity to a DOT Graph.

        :param graph: the DOT Graph to add the ROS Entity to
        :type graph: graphviz.Digraph
        """
        return

    def _string_rows(self):
        """
        Define rows of strings (one row per line) needed to create the human-readable string representation of the ROS Entity.

        :return: the rows of strings to represent the ROS Entity
        :rtype: list[str]
        :raises ValueError: if left unimplemented by a subclass
        """
        rows = []

        # Start with common data for all entities
        if self.name is None:
            return rows

        rows.append("  " + (len(self.name) + 9) * "=")
        rows.append(f"        name : {self.name}")
        rows.append(f"        source : {self.source}")
        rows.append(f"        version : {self.version}")

        # Get all attributes that are not methods, or private ('_') or yaml specific
        # By default, attr appear in sorted order
        for attr, value in inspect.getmembers(
            self, lambda a: (not inspect.isroutine(a))
        ):
            if not attr.startswith("_") and not attr.startswith("yaml"):
                if attr == "name" or attr == "source" or attr == "version":
                    # put common at the top
                    continue

                if isinstance(value, dict):
                    rows.append(f"        {attr} :")
                    keys = list(value.keys())
                    keys.sort()
                    for key in keys:
                        rows.append(f"            - {key} : {value[key]}")
                elif isinstance(value, set) or isinstance(value, list):
                    rows.append(f"        {attr} :")
                    values = list(value)
                    values.sort()
                    for key in values:
                        rows.append(f"            - {key}")
                else:
                    rows.append(f"        {attr} : {value}")
        return rows

    def __str__(self):
        """
        Return the human-readable string representation of the ROS Entity.

        :return: the string representation of the ROS Entity
        :rtype: str
        """
        return "\n".join(self._string_rows())

    @classmethod
    def get_model_class(cls, yaml_tag):
        if cls._tag_to_class is None:
            cls._tag_to_class = {
                getattr(sub, "yaml_tag", ""): sub
                for sub in _iter_model_subclasses(cls)
                if getattr(sub, "yaml_tag", "")
            }
        return cls._tag_to_class.get(yaml_tag)

    @classmethod
    def get_model_class_from_type(cls, type_name):
        if cls._name_to_class is None:
            cls._name_to_class = {
                sub.__name__: sub for sub in _iter_model_subclasses(cls)
            }
        return cls._name_to_class.get(type_name)

    @_pre_root_validator
    def check_all_fields(cls, values):
        """Provide more expressive typing errors."""

        def is_instance_of_type(value, expected_type):
            """Check if a value matches the expected type."""
            if expected_type is Any:
                return True
            origin = get_origin(expected_type)
            args = get_args(expected_type)

            if origin is Union:
                return any(is_instance_of_type(value, t) for t in args)
            elif origin is Optional:
                return value is None or is_instance_of_type(value, args[0])
            elif origin is dict:
                if not isinstance(value, dict):
                    return False
                key_type, value_type = args
                return all(
                    is_instance_of_type(k, key_type)
                    and is_instance_of_type(v, value_type)
                    for k, v in value.items()
                )
            elif origin is set:
                if not isinstance(value, set):
                    return False
                item_type = args[0]
                return all(is_instance_of_type(item, item_type) for item in value)
            elif origin is list:
                if not isinstance(value, list):
                    return False
                item_type = args[0]
                return all(is_instance_of_type(item, item_type) for item in value)
            if expected_type not in (float, int, str, bool, None.__class__):
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    f"Expected type not handled above {expected_type} {type(value)} | {value} | {origin}",
                )
            return isinstance(value, expected_type)

        errors = []
        for field_name, field_type in cls.__annotations__.items():
            value = values.get(field_name)
            if value is not None and not is_instance_of_type(value, field_type):
                expected_types = ", ".join(
                    [
                        t.__name__ if hasattr(t, "__name__") else str(t)
                        for t in (
                            get_args(field_type)
                            if get_origin(field_type) is Union
                            else [field_type]
                        )
                    ]
                )
                errors.append((field_name, value, type(value).__name__, expected_types))
                warnings.warn(
                    CustomSerializationWarning(
                        message="Serialization type mismatch",
                        field_name=field_name,
                        expected_type=expected_types,
                        actual_type=type(value).__name__,
                    )
                )
        if errors:
            error_messages = ", ".join(
                [
                    f"{name}: {val} (type: {typ}) expected {expected}"
                    for name, val, typ, expected in errors
                ]
            )
            raise ValueError(f"Invalid values - {error_messages}")
        return values


class CustomSerializationWarning(UserWarning):
    """Custom serialization warning."""

    def __init__(self, message, field_name, expected_type, actual_type):
        self.field_name = field_name
        self.expected_type = expected_type
        self.actual_type = actual_type
        super().__init__(message)

    def __str__(self):
        return (
            f"\n\nMSG: {super()}\n"
            f"Field: {self.field_name}\n"
            f"Expected_Type: {self.expected_type}\n"
            f"Actual_Type: {self.actual_type}\n"
        )


class _BankMetamodel(BaseModel):
    """Internal Base Metamodel for Banks that contain instances of ROS Entity Metamodels."""

    yaml_tag: ClassVar[str] = ""
    HUMAN_OUTPUT_NAME: ClassVar[str] = ""
    _tag_to_class: ClassVar[Optional[Dict[str, type]]] = None
    _name_to_class: ClassVar[Optional[Dict[str, type]]] = None
    names_to_metamodels: Dict[str, _EntityMetamodel] = {}

    def __init_subclass__(cls, **kwargs):
        """Invalidate lookup caches when new bank metamodel classes load."""
        super().__init_subclass__(**kwargs)
        _BankMetamodel._tag_to_class = None
        _BankMetamodel._name_to_class = None

    def __init__(self, **kwargs):
        """
        Create a new instance of the Bank Metamodel using keyword arguments.

        Used for the purposes of loading from YAML.

        :param kwargs: the keyword arguments to create a new
            Bank Metamodel from
        :type kwargs: dict{str: str}
        :raises KeyError: if the 'names_to_metamodels' key is missing
        """
        super().__init__(**kwargs)
        self.names_to_metamodels = kwargs.get("names_to_metamodels", {})

    def __contains__(self, key):
        """Check if bank contains the specified entity."""
        return key in self.names_to_metamodels

    def __getitem__(self, name):
        """
        Return the appropriate entity from the bank.

        This instantiates a new entity if one is not already present for
        the name

        :param name: the key to identify the desired entity
        :type name: str
        :return: the matching entity, either newly added or
            retrieved
        :rtype: entity class for bank
        """
        if name not in self.names_to_metamodels:
            self.names_to_metamodels[name] = self._create_entity(name)
        return self.names_to_metamodels[name]

    @property
    def keys(self):
        """
        Return list of keys.

        :return: list of entity keys
        """
        return list(self.names_to_metamodels.keys())

    @property
    def items(self):
        """
        Return list of key,value tuples.

        :return: list of key, value tuples
        """
        return list(self.names_to_metamodels.items())

    def _create_entity(self, name):
        """
        Create instance of named entity given bank type.

        :param name: name of entity
        :return: instance of entity type for bank
        """
        return None

    def entity_class(self, name):
        """
        Return the class of entity given bank type.

        :return: entity class definition for bank type
        """
        return None

    def add_to_dot_graph(self, graph):
        """
        Add the Bank's internal ROS Entities to a DOT Graph.

        :param graph: the DOT Graph to add ROS Entities to
        :type graph: graphviz.Digraph
        """
        for name in sorted(self.names_to_metamodels.keys()):
            self.names_to_metamodels[name].add_to_dot_graph(graph)

    def __str__(self):
        """
        Return the human-readable string representation of the Bank.

        Includes its internal ROS Entities

        :return: the string representation of the Bank
        :rtype: str
        """
        rows = [self.__class__.HUMAN_OUTPUT_NAME]
        rows.append("=" * (len(rows[0])))
        rows.append("")
        for name in sorted(self.names_to_metamodels.keys()):
            rows.append(str(self.names_to_metamodels[name]))
            rows.append("")
        return "\n".join(rows)

    @classmethod
    def get_model_class(cls, yaml_tag):
        if cls._tag_to_class is None:
            cls._tag_to_class = {
                getattr(sub, "yaml_tag", ""): sub
                for sub in _iter_model_subclasses(cls)
                if getattr(sub, "yaml_tag", "")
            }
        return cls._tag_to_class.get(yaml_tag)

    @classmethod
    def get_model_class_from_type(cls, type_name):
        if cls._name_to_class is None:
            cls._name_to_class = {
                sub.__name__: sub for sub in _iter_model_subclasses(cls)
            }
        return cls._name_to_class.get(type_name)

    @_pre_root_validator
    def check_all_fields(cls, values):
        """Provide more expressive typing errors."""

        def is_instance_of_type(value, expected_type):
            """Check if a value matches the expected type."""
            if expected_type is Any:
                return True
            origin = get_origin(expected_type)
            args = get_args(expected_type)

            if origin is Union:
                return any(is_instance_of_type(value, t) for t in args)
            elif origin is Optional:
                return value is None or is_instance_of_type(value, args[0])
            elif origin is dict:
                if not isinstance(value, dict):
                    return False
                key_type, value_type = args
                return all(
                    is_instance_of_type(k, key_type)
                    and is_instance_of_type(v, value_type)
                    for k, v in value.items()
                )
            elif origin is set:
                if not isinstance(value, set):
                    return False
                item_type = args[0]
                return all(is_instance_of_type(item, item_type) for item in value)
            elif origin is list:
                if not isinstance(value, list):
                    return False
                item_type = args[0]
                return all(is_instance_of_type(item, item_type) for item in value)
            if expected_type not in (float, int, str, bool, None.__class__):
                Logger.get_logger().log(
                    LoggerLevel.DEBUG,
                    f"Expected type not handled above {expected_type} {type(value)}",
                )
            return isinstance(value, expected_type)

        errors = []
        for field_name, field_type in cls.__annotations__.items():
            value = values.get(field_name)
            if value is not None and not is_instance_of_type(value, field_type):
                expected_types = ", ".join(
                    [
                        t.__name__ if hasattr(t, "__name__") else str(t)
                        for t in (
                            get_args(field_type)
                            if get_origin(field_type) is Union
                            else [field_type]
                        )
                    ]
                )
                errors.append((field_name, value, type(value).__name__, expected_types))

        if errors:
            error_messages = ", ".join(
                [
                    f"{name}: {val} (type: {typ}) expected {expected}"
                    for name, val, typ, expected in errors
                ]
            )
            raise ValueError(f"Invalid values - {error_messages}")
        return values
