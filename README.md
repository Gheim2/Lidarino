# Lidarino

Lidarino is a ROS package providing the `lidarino_description` robot description and related launch files and utilities.

## Contents

- `src/lidarino_description/`: package source, ROS launch files, URDF/xacro and Python utilities.
- `launch/`: Gazebo and display launch files.
- `urdf/`: robot model and meshes.

## Requirements

- ROS 2 (a supported distro for this project)
- colcon build

## Build

From workspace root:

```bash
colcon build
source install/setup.bash
```

## Run (Gazebo)

Example to launch Gazebo with the robot:

```bash
ros2 launch lidarino_description gazebo.launch.py
```

## Contributing

Pull requests and issues welcome. Please follow ROS package conventions and keep changes focused.