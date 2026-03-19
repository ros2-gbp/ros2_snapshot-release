# ROS 2 Snapshot Tools

## Description

ROS 2 Snapshot provides Python-based [ROS 2](http://www.ros.org) tools for
capturing:

- a specification model of the ROS 2 packages available in a workspace
- a deployment model of a currently running ROS system

The captured model can be loaded, manipulated, and exported for documentation,
interface control documentation (ICD), and model-based engineering workflows.

This repository includes the following modules:

- `core` - ROS entity metamodel classes and tools for marshalling and
  unmarshalling model instances
- `workspace_modeler` - captures a specification model of an existing ROS 2
  workspace
- `snapshot` - captures a model of a currently running ROS 2 deployment

## Requirements

This version of the package has been tested under ROS Jazzy, Kilted, and Rolling running Ubuntu 24.04.

Before using `ros2_snapshot`, make sure:

- ROS 2 is installed and your environment has been sourced
- the runtime ROS 2 CLI dependencies from [`package.xml`](package.xml)
  are available
- Python dependencies from [`requirements.txt`](requirements.txt)
  are installed

Install the Python dependencies with:

```bash
pip install -r requirements.txt
```

Note: the `apt` Python module is optional and is only used on Debian/Ubuntu
systems to enrich workspace package version detection. On non-Debian platforms
such as RHEL, `workspace_modeler` will still run without it.

## Source Build

Clone this project into your
[colcon](https://colcon.readthedocs.io/en/released/user/installation.html)
workspace, then build and source it:

```bash
colcon build
source <ros_ws_location>/setup.bash
```

After that, the package is available through `ros2 run ros2_snapshot ...`.

## Quick Start

`ros2_snapshot` is typically used in two steps:

1. Generate a specification model of the workspace.
2. Snapshot the currently running ROS deployment using that specification model.

Generate the workspace model first:

```bash
ros2 run ros2_snapshot workspace
```

Then snapshot a running system:

```bash
ros2 run ros2_snapshot running
```

The `running` command expects an existing specification model. By default it
loads that model from `~/.snapshot_modeling/yaml`, so the workspace step should
normally be run first. If your specification files live elsewhere, use
`--spec-input` to point `running` at the correct folder.

By default, both tools write `yaml` and `pickle` outputs under
`~/.snapshot_modeling`. Use `-a` to also save `json`, human-readable text, and
the DOT graph output for the running snapshot.

For command-line details, use `-h` or see the module READMEs:

- [`ros2_snapshot/workspace_modeler/README.md`](ros2_snapshot/workspace_modeler/README.md)
- [`ros2_snapshot/snapshot/README.md`](ros2_snapshot/snapshot/README.md)

## Basic Demonstration

First generate the workspace specification model:

```bash
ros2 run ros2_snapshot workspace -a
```

Inspect the generated files under `~/.snapshot_modeling`.

Then start a few ROS nodes:

```bash
ros2 run turtlesim turtlesim_node --ros-args -r __ns:=/demo
```

```bash
ros2 run turtlesim turtle_teleop_key --ros-args -r __ns:=/demo
```

```bash
ros2 run demo_nodes_py talker
```

```bash
ros2 run demo_nodes_py listener
```

With those nodes running, capture a deployment snapshot:

```bash
ros2 run ros2_snapshot running -a
```

Inspect the resulting deployment model files under `~/.snapshot_modeling`.


## Known issues

This project is an ongoing development effort and may be subject to future changes.

See the individual module READMEs for additional information.

## License Information

Released under Apache 2.0 license

Copyright (c) 2026
Capable Humanitarian Robotics and Intelligent Systems Lab (CHRISLab)
Christopher Newport University

All rights reserved.

See LICENSE for more information.

## Publications

Please use the following publications for reference when using ROS 2 Snapshot:

- S. E. Fox, A. J. Farney, and D. C. Conner, "Documenting ROS 2 Systems with ROS 2 Snapshot",  SoutheastCon 2026, Huntsville, AL, USA, 2026, to appear.

This work is based on earlier work for ROS 1:

- W. R. Drumheller and D. C. Conner, ["Documentation and Modeling of ROS Systems,"](https://ieeexplore.ieee.org/document/9401832) SoutheastCon 2021, Atlanta, GA, USA, 2021, pp. 1-7, doi: 10.1109/SoutheastCon45413.2021.9401832.

- W. R. Drumheller and D. C. Conner, ["Online system modeling and documentation using ROS snapshot,"](https://dl.acm.org/doi/10.5555/3447080.3447095) J. Comput. Sci. Coll. 36, 3 (October 2020), 128–141.

## Credit

- William R. Drumheller
- David C. Conner <[robotics@cnu.edu](mailto:robotics@cnu.edu)>
- Sebastian E. Fox <[sebastian.fox.22@cnu.edu](mailto:sebastian.fox.22@cnu.edu)>
- Andrew J. Farney <[andrew.farney.22@cnu.edu](mailto:andrew.farney.22@cnu.edu)>

The code is formatted using [Black](https://github.com/psf/black).
