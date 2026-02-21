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
    BASE_EXCLUSIONS = {}
    DEBUG_EXCLUSIONS = {}
    TF_EXCLUSIONS = {}
    INSTANCE = None

    def __init__(self, filter_out_debug, filter_out_tf):
        """Initialize filter instance."""
        self._base_exclusions = self.__class__.BASE_EXCLUSIONS
        self._debug_exclusions = {}
        self._tf_exclusions = {}
        if filter_out_debug:
            self._debug_exclusions = self.__class__.DEBUG_EXCLUSIONS
        if filter_out_tf:
            self._tf_exclusions = self.__class__.TF_EXCLUSIONS

    def should_filter_out(self, item):
        """
        Check to see if item is in list of exclusions.

        :param item:
        :return: True if we should filter, False otherwise
        """
        return (
            (item in self._base_exclusions)
            or (item in self._debug_exclusions)
            or (item in self._tf_exclusions)
        )

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

    BASE_EXCLUSIONS = {"/roslaunch"}
    DEBUG_EXCLUSIONS = {"/rosout"}


class TopicFilter(Filter):
    """Default filter for Topics."""

    DEBUG_EXCLUSIONS = {"/rosout", "/rosout_agg", "/statistics"}
    TF_EXCLUSIONS = {"/tf", "/tf_static"}


class ServiceTypeFilter(Filter):
    """Default filter for Services."""

    DEBUG_EXCLUSIONS = {"roscpp/GetLoggers", "roscpp/SetLoggerLevel"}
