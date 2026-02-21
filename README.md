# ROS 2 Snapshot Tools


### Description

Within this repository are Python-based [ROS 2](http://www.ros.org) tools that
can be used to capture a software model of a ROS 2 Workspace and running ROS deployment.

The captured model can be loaded, manipulated, and exported for documentation or use
in so-called Model Integrated Computing (MIC) or Model Driven Engineering (MDE).

This repository includes the following modules:
* `core`                    - ROS Entity metamodel classes and tools for
                               marshalling/unmarshalling instances of these
                               metamodels (model)
* `workspace_modeler`       - a tool to capture specification model of existing ROS
                               workspace
* `snapshot`                - a tool to capture models from currently running ROS
                               deployments

The system is useful for Interface Control Documentation (ICD) of deployed systems.

### Initial Setup

The Python 3 executables require `graphviz`, `pydantic`, `pytest`, and `PyYAML` packages. Use
<pre>
pip install -r requirements.txt
</pre>

### Source Build

Clone this project into your [Colcon](https://colcon.readthedocs.io/en/released/user/installation.html) Workspace, and run the following commands:
- `colcon build`
- `source <ros_ws_location>/setup.bash` (your `.bashrc` may handle this automatically on shell restart)

Thereafter, `ros2_snapshot` is available for use.

To capture a model of the ROS 2 workspace, including installed and custom packages, as configured on your machine:
```
ros2 run ros2_snapshot workspace
```

To capture a model of currently running system:
```
ros2 run ros2_snapshot running
```

By default, the snapshot tools save information in `yaml` and `pickle` formats
in the default `~/.snapshot_modeling` folder. Additionally, `json` and human readable basic
text formats, along with a graphviz based DOT view of the ROS computation graph,
are available as options.

Use the `-a` option to save all available formats.

See the READMEs in each module for more information, or `-h` to see options.

### Basic Demonstration

To see a basic demonstration, first run the workspace modeler

`clear; ros2 run ros2_snapshot workspace -a`

And inspect the specification files in the default `~/.snapshot_modeling` folder.

Then, run some ROS nodes

`clear; ros2 run turtlesim turtlesim_node --ros-args -r __ns:=/demo`

`clear; ros2 run turtlesim turtle_teleop_key --ros-args -r __ns:=/demo`

`clear; ros2 run demo_nodes_py talker`

`clear; ros2 run demo_nodes_py listener`

And run the snapshot tool

`clear; ros2 run ros2_snapshot running -a`

Again inspect the data bank files in the default `~/.snapshot_modeling` folder.


### Known issues

This project is an ongoing development effort and may be subject to future changes.

This package has been tested under ROS Jazzy and Kilted running Ubuntu 24.04

See the individual module READMEs for additional information.

### License Information

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

### Credit

- William R. Drumheller
- David C. Conner <[robotics@cnu.edu](mailto:robotics@cnu.edu)>
- Sebastian E. Fox <[sebastian.fox.22@cnu.edu](mailto:sebastian.fox.22@cnu.edu)>
- Andrew J. Farney <[andrew.farney.22@cnu.edu](mailto:andrew.farney.22@cnu.edu)>

The code is formatted using [Black](https://github.com/psf/black).
