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

import pytest

from ros2_snapshot.core.deployments.service import Service, ServiceBank
from ros2_snapshot.core.ros_model import BankType, ROSModel
from ros2_snapshot.core.specifications.package_specification import (
    PackageSpecificationBank,
)
from ros2_snapshot.snapshot.builders.node_builder import NodeBuilder
from ros2_snapshot.snapshot.snapshot import ROSSnapshot


def test_update_bank_merges_entities_into_existing_bank():
    model = ROSModel({BankType.SERVICE: ServiceBank()})
    service = Service(name="/demo_service")

    model.update_bank(BankType.SERVICE, {"/demo_service": service})

    assert model.service_bank.keys == ["/demo_service"]
    assert model.service_bank["/demo_service"] is service


def test_update_bank_initializes_missing_bank_from_bank_type():
    model = ROSModel({})
    service = Service(name="/demo_service")

    model.update_bank(BankType.SERVICE, {"/demo_service": service})

    assert isinstance(model[BankType.SERVICE], ServiceBank)
    assert model.service_bank.keys == ["/demo_service"]
    assert model.service_bank["/demo_service"] is service


def test_snapshot_package_specification_bank_uses_package_specification_type():
    package_bank = PackageSpecificationBank()
    snapshot = ROSSnapshot()
    snapshot._ros_specification_model = ROSModel(
        {BankType.PACKAGE_SPECIFICATION: package_bank}
    )

    assert snapshot.package_specification_bank is package_bank


def test_snapshot_resets_cached_node_processes_before_probing(monkeypatch):
    calls = []

    class FailingNodeStrategy:
        def __init__(self, *_args, **_kwargs):
            pass

        def __enter__(self):
            raise RuntimeError("stop after reset")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(NodeBuilder, "reset_processes", lambda: calls.append("reset"))
    monkeypatch.setattr(
        "ros2_snapshot.snapshot.snapshot.NodeStrategy",
        FailingNodeStrategy,
    )

    with pytest.raises(RuntimeError, match="stop after reset"):
        ROSSnapshot().snapshot()

    assert calls == ["reset"]
