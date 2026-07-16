# Lidarino 🤖

Lidarino is a custom ROS 2 differential-drive robot project. This workspace contains the robot description (URDF), custom hardware interfaces for ESP32 microcontrollers, and the bringup launch files required for autonomous navigation and SLAM.

## Workspace Architecture

The project is structured according to ROS 2 best practices:
- `src/lidarino_description/`: Robot model (URDF/Xacro), 3D meshes, and configuration files (Nav2, EKF, RViz, Costmaps).
- `src/lidarino_hardware/`: C++ `ros2_control` hardware interface plugin handling binary serial communication with the ESP32.
- `src/lidarino_bringup/`: Launch files to start the real robot or simulation environments.

## Requirements

- ROS 2 (Jazzy or supported distro)
- `colcon build`
- `vcs` (vcstool) to manage third-party dependencies.

## Installation

This repository uses a `.repos` file to cleanly manage external dependencies (like LiDAR drivers and exploration nodes) without bloating the main Git tree.

```bash
# 1. Clone this repository
git clone https://github.com/Gheim2/Lidarino.git lidarino_ws
cd lidarino_ws
```

### 2. First config of the workspace (*IMPORTANT*)
```bash
sudo chmod +x setup_workspace.sh
./setup_workspace.sh
```

## Build

From workspace root:

```bash
colcon build --symlink-install
source install/setup.bash
```

## Run

### Simulation (Gazebo)

You can use ros_manager.py to run everything that you need:

```bash
python3 ros_manager.py
```

To visualize the simulation manually you can run:

```bash
rviz2 --ros-args -p use_sim_time:=true
```

## Contributing

Pull requests and issues welcome. Please follow ROS package conventions and keep changes focused.
