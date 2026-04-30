## Workspace Modeler

### Description

This Python tool crawls an existing ROS Workspace and generates models for all
available packages include node, message, action, and service specifications.

The output models are useful for system documentation and validation, and
for future use in model-based engineering.

These component metamodels are then used to create models of ROS deployments using `ros2_snapshot running`.

### Usage

The `workspace_modeler`  assumes that it is running on the same ROS network as a
currently deployed ROS system.

To run `workspace_modeler` tool, after building or installing `ros2_snapshot`,
use this command: `ros2 run ros2_snapshot workspace`

The default command generates an output model in both YAML and Pickle formats in the default output directory,
found in the hidden `~/.snapshot_modeling` folder.

- The following command line options are available:
    - `-h`, `--help`
        - show this help message and exit
    - `-v`, `--version`
        - Display version information for the package modeler tool and exit
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
    - `-a`, `--all`
        - output all possible formats using default names
    - `-lt THRESHOLD`, `--logger_threshold=THRESHOLD`
        - Outputs different levels of logger
        - (default=`INFO`)
        - Other levels are`WARNING`, `ERROR`, `DEBUG`

### Output

After running `workspace_modeler`, the following output structure will be available:
- The main `output` directory (or as specified by command line arguments)
  - By default, the output is located in the hidden directory `.snapshot_modeling`
- Inside the `output` directory, you will find the following sub-directories if specified:
    - `yaml`: YAML, detailed model of the deployed ROS system as instances of the metamodels
    - `pickle`: A standard Python Pickle file
        - NOTE: Pickle files can be broken by subsequent version changes to Python or metamodels
    - `json`: JSON,  detailed model of the deployed ROS system as instances of the metamodels
    - `human`: human-readable, formatted version of the ROS system model
        - based on instances of the metamodels
        - NOTE: These files are NOT loadable; always save a YAML or Pickle version for future use
    - `graph`: the ROS Graph DOT Output of ROS Computation graph with grouped actions

### Known issues

This project is an ongoing development effort and may be subject to future changes.
 The following specific shortcomings are noted:
  * The package modeler does NOT do static code analysis
  * The package modeler identifies all executable files in packages as potential nodes
    * Nodes are initially identified with validated=False
    * Snapshot `running` will validate some node definitions based on a fuzzy matching of names

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
