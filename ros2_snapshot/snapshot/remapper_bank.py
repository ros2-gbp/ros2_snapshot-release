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
Simple class to hold dictionary of name to remapped key.

Use to invert the references from key to data
Supports a one-to-many re-mapping

"""


class RemapperBank:
    """Remapper from data to key for various banks."""

    def __init__(self):
        """Instantiate an instance of the RemapperBank."""
        self._data_to_key_maps = {}

    def __getitem__(self, data_name):
        """
        Return the appropriate Remapped name.

        :param data_name: the key to identify the desired mapping
        :type name: str
        :return: the corresponding string
        """
        return self._data_to_key_maps[data_name]

    @property
    def keys(self):
        """:return: the keys for remapper bank."""
        return list(self._data_to_key_maps.keys())

    @property
    def items(self):
        """:return: the key, value pairs for remapper bank."""
        return list(self._data_to_key_maps.items())

    def add_remap(self, data_name, key):
        """
        Add a remapping from data_name to key.

        Supports a one-to-many mapping

        :param data_name: the new key
        :type data_name: str
        :param key: the old key to data
        :type data_name: str
        """
        if (
            data_name not in self._data_to_key_maps
            or self._data_to_key_maps[data_name] is None
        ):
            # New remap
            self._data_to_key_maps[data_name] = key
        else:
            # remap exists
            if key == self._data_to_key_maps[data_name]:
                return

            if isinstance(self._data_to_key_maps[data_name], list):
                if key not in self._data_to_key_maps[data_name]:
                    print(
                        "    Adding ",
                        key,
                        " to existing ",
                        data_name,
                        self._data_to_key_maps[data_name],
                    )
                    self._data_to_key_maps[data_name].append(key)
            else:
                print(
                    "    Adding ",
                    key,
                    " to existing ",
                    data_name,
                    " as list",
                    self._data_to_key_maps[data_name],
                )
                self._data_to_key_maps[data_name] = [self._data_to_key_maps[data_name]]
                self._data_to_key_maps[data_name].append(key)
