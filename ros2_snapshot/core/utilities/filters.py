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
Filter object for processing ROS data.

@author William R. Drumheller <william@royalldesigns.com>
"""


class Filter:
    """Generic filter class."""

    FILTER_OUT_DEBUG = False
    FILTER_OUT_TF = False
    BASE_EXCLUSIONS = frozenset()
    DEBUG_EXCLUSIONS = frozenset()
    TF_EXCLUSIONS = frozenset()
    _runtime_exclusions = set()
    INSTANCE = None

    def __init_subclass__(cls, **kwargs):
        """Give each subclass its own runtime state so instances never share it."""
        super().__init_subclass__(**kwargs)
        cls._runtime_exclusions = set()
        cls.INSTANCE = None

    def __init__(self, filter_out_debug, filter_out_tf):
        """Initialize filter instance."""
        cls = self.__class__
        self._exclusions = set(cls.BASE_EXCLUSIONS) | cls._runtime_exclusions
        if filter_out_debug:
            self._exclusions |= cls.DEBUG_EXCLUSIONS
        if filter_out_tf:
            self._exclusions |= cls.TF_EXCLUSIONS

    def should_filter_out(self, item):
        """
        Check to see if item is in list of exclusions.

        :param item:
        :return: True if we should filter, False otherwise
        """
        return item in self._exclusions

    @classmethod
    def add_runtime_exclusion(cls, name):
        """Add a name to runtime exclusions and invalidate the cached singleton."""
        cls._runtime_exclusions.add(name)
        cls.INSTANCE = None

    @classmethod
    def get_filter(cls):
        """
        Create an instance of given filter.

        :return: filter instance
        """
        if cls.INSTANCE is None:
            cls.INSTANCE = cls(cls.FILTER_OUT_DEBUG, cls.FILTER_OUT_TF)
        return cls.INSTANCE


class NodeFilter(Filter):
    """Default filter for Nodes."""

    BASE_EXCLUSIONS = frozenset({"/roslaunch"})
    DEBUG_EXCLUSIONS = frozenset({"/rosout"})

    def should_filter_out(self, item):
        """Return True for nodes that should not be modeled."""
        return super().should_filter_out(item) or item.endswith("/ros2_snapshot_remote")


class TopicFilter(Filter):
    """Default filter for Topics."""

    DEBUG_EXCLUSIONS = frozenset({"/rosout", "/rosout_agg", "/statistics"})
    TF_EXCLUSIONS = frozenset({"/tf", "/tf_static"})


class ServiceTypeFilter(Filter):
    """Default filter for Services."""

    DEBUG_EXCLUSIONS = frozenset({"roscpp/GetLoggers", "roscpp/SetLoggerLevel"})
