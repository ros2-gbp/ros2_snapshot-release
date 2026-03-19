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

"""Basic handler for logging functionality."""

import logging


class LoggerLevel(object):
    """Define different levels of logging output."""

    INFO = logging.INFO
    DEBUG = logging.DEBUG
    WARNING = logging.WARNING
    ERROR = logging.ERROR


class Logger(object):
    """Define standard interface to python logging."""

    INSTANCE = None
    LEVEL = LoggerLevel.DEBUG

    def __init__(self):
        """Set up the logger instance."""
        self._logger = logging.getLogger()

    @staticmethod
    def setup(level):
        """
        Set up the logger at given level.

        :param level: logging level to display
        """
        logging.basicConfig(
            format="[%(asctime)s][%(levelname)s]-> %(message)s",
            datefmt="%d%b%Y %I:%M:%S %p %Z",
            level=level,
        )

    def log(self, level, message):
        """
        Log message at level.

        :param level: logging level
        :param message: text string to log
        """
        self._logger.log(level, message)

    @classmethod
    def get_logger(cls):
        """Get logger instance."""
        if cls.INSTANCE is None:
            cls.INSTANCE = cls()
            cls.INSTANCE.setup(cls.LEVEL)
        return cls.INSTANCE
