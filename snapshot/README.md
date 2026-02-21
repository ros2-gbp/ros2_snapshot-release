## Running Snapshot

### Description

This python tool collects, sorts, and writes out detailed modeling information about Nodes (including Components, Action Servers, and Action Clients), Topics, Messages, Services, and Actions that are registered during runtime.

The program is also able to create and write out a directed DOT graph that details the Nodes and Topics
(including display of which Topics are used for Actions) that are registered during runtime.

All of this information helps to describe the
[ROS Computation Graph](http://wiki.ros.org/ROS/Concepts#ROS_Computation_Graph_Level).
Unlike, the basic `rosgraph` tool, the model-based tool provides grouped information for actions.

The output models are useful for system documentation and validation, and
for future use in model-based engineering.

### Usage

- The `snapshot` program assumes that it is running on the same ROS network as a
currently deployed ROS system.

To run the `snapshot` tool, you will need to perform the following steps in addition to the Initial Setup in
the main [README](../README.md), then use this command: `ros2 run ros2_snapshot running`

The default command generates an output model in both YAML and Pickle formats in the `output` directory, found in the
hidden `.snapshot_modeling` folder.

- The following command line options are available:
    - `-h`, `--help`
        - show this help message and exit
    - `-v`, `--version`
        - Display version information for the snapshot tool and exit
    - `-t TARGET`, `--target=TARGET`
        - target output directory (default=`~/.snapshot_modeling`)
    - `-b BASE`, `--base=BASE`
        - output base file name
        - (default=`snapshot`)
    - `-y YAML`, `--yaml=YAML`
        - output yaml format to directory
        - (default=`yaml`)
    - `-p PICKLE`, `--pickle=PICKLE`
        - output pickle format to directory
        - (default=`pickle`)
    - `-r HUMAN`, `--human=HUMAN`
        - output human readable text format to directory
        - (default=`None`)
    - `-g GRAPH`, `--graph=GRAPH`
        - output dot format for computation graph to directory
        - (default=`None`)
    - `-a`, `--all`
        - output all possible formats
    - `-d`, `--display`
        - display computation graph pdf
        - (default=`False`)
        - (only valid if graph output is specified)
    - `-s=SPEC`, `--spec-input=SPEC`
        - specification model input folder (default='~/.snapshot_modeling/yaml')
    - `-lt THRESHOLD`, `--logger_threshold=THRESHOLD`
        - Outputs different levels of logger
        - (default=`INFO`)
        - Other levels are`WARNING`, `ERROR`, `DEBUG`

### Output

After running `snapshot`, the following output structure will be available:
- The main target output directory (or as specified by command line arguments)
  - By default, the output is located in the hidden directory `~/.snapshot_modeling`
- Inside the target directory, you will find the following sub-directories if specified:
    - `yaml`: YAML, detailed model of the deployed ROS system as instances of the metamodels
    - `pickle`: A standard Python Pickle file
        - NOTE: Pickle files can be broken by subsequent version changes to Python or metamodels
    - `json`: JSON,  detailed model of the deployed ROS system as instances of the metamodels
    - `human`: human-readable, formatted version of the ROS system model
        - based on instances of the metamodels
        - NOTE: These files are NOT loadable; always save a YAML or Pickle version for future use
    - `dot_graph`: the ROS Graph DOT Output of ROS Computation graph with grouped actions

### Known issues

The following specific shortcomings are noted:
  * Process ID matching is fuzzy and does not always validate running nodes
    * This will likely require static code analysis to fully fix this
  * Python scripts may be loaded and subscribe/publish, but executable shows the loader (e.g. /usr/bin/python3) not script
    * We attempt to match based on command line arguments, but node and script names are not always aligned.
    * Relevant information is reported if a match is not found.
    * This might require static launch file analysis or other customizations to be completely clear.

### License Information

Released under Apache 2.0 license

Copyright (c) 2026
Capable Humanitarian Robotics and Intelligent Systems Lab (CHRISLab)
Christopher Newport University

All rights reserved.

See LICENSE with each package for more information.

### Credit

- William R. Drumheller
- David C. Conner <[robotics@cnu.edu](mailto:robotics@cnu.edu)>
- Sebastian E. Fox <[sebastian.fox.22@cnu.edu](mailto:sebastian.fox.22@cnu.edu)>
- Andrew J. Farney <[andrew.farney.22@cnu.edu](mailto:andrew.farney.22@cnu.edu)>
