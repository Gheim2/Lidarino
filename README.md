# Lidarino 🤖 (Isaac Sim Edition)

Lidarino is a custom ROS 2 differential-drive robot project. This branch is specifically tailored for **Windows** native execution using **NVIDIA Isaac Sim** and **Pixi** for environment and dependency management.

## Workspace Architecture

The project is structured according to ROS 2 best practices:
- `src/lidarino_description/`: Robot model (URDF/Xacro), 3D meshes, and configuration files (Nav2, EKF, RViz, Costmaps).
- `src/lidarino_hardware/`: C++ `ros2_control` hardware interface plugin handling binary serial communication with the ESP32.
- `src/lidarino_bringup/`: Launch files to start the real robot or simulation environments.

## Requirements

- Windows 11
- [Pixi](https://pixi.sh/) package manager
- [NVIDIA Isaac Sim](https://docs.omniverse.nvidia.com/isaacsim/latest/index.html)
- NVIDIA `IsaacSim-ros_workspaces` repository

## Installation

This repository uses a `.repos` file and a PowerShell script to cleanly manage external dependencies (like LiDAR drivers and exploration nodes) without bloating the main Git tree.

### 1. Setup Isaac Sim Workspace
First, follow the official NVIDIA documentation to clone the `IsaacSim-ros_workspaces` repository and set up the `jazzy_ws` workspace.

### 2. Clone this repository
```powershell
cd C:\IsaacSim-ros_workspaces\jazzy_ws\src
git clone -b feature/isaac-sim https://github.com/Gheim2/Lidarino.git lidarino_repo
```

### 3. First config of the workspace (*IMPORTANT*)
Install `vcstool` via Pixi, enter the isolated environment, and run the setup script to fetch third-party packages:
```powershell
cd C:\IsaacSim-ros_workspaces\jazzy_ws
pixi add vcstool
pixi shell
cd src\lidarino_repo
.\setup_workspace.ps1
```

## Build

From the `jazzy_ws` workspace root, build the workspace using the Pixi-managed MSVC toolchain:

```powershell
cd C:\isaacSim\IsaacSim-ros_workspaces\jazzy_ws
pixi run build
```

## Run

### Simulation (Gazebo)

To run the simulation with the native Windows ROS 2 bridge, start the following in separate PowerShell windows from the `jazzy_ws` root:

1. **Terminal 1 (Zenoh Router):** `pixi run zenoh`
2. **Terminal 2 (Isaac Sim):** `pixi run sim`
3. **Terminal 3 (ROS 2 Nodes):** `pixi shell` -> launch your nodes here.

---

## Advanced: Custom URDF to USD Conversion

Unlike Gazebo, NVIDIA Isaac Sim natively uses Pixar's **USD (Universal Scene Description)** format. The `.usd` model is already provided in this repository. However, if you modify the URDF or want to import your own, follow these steps:

### 1. Generate the static URDF
Isaac Sim parses plain `.urdf` files better than `.xacro`. Open your Pixi shell and compile the Isaac-specific Xacro file using the `-o` flag to ensure the correct UTF-8 encoding on Windows:

```powershell
# Open the Pixi shell
pixi shell

# Navigate to the URDF directory
cd src/lidarino_repo/src/lidarino_description/urdf

# Compile the Xacro into a static URDF
xacro lidarino_isaac.urdf.xacro -o lidarino_isaac.urdf
```

### 2. Import into Isaac Sim
1. Launch Isaac Sim (`pixi run sim`).
2. Go to **File > Import**.
3. Select the newly generated `lidarino_isaac.urdf` as the Input File.
4. Select the **Robot type** if needed.
5. Click **Import** and save the scene as a `.usd` file.

---

## Contributing

Pull requests and issues welcome. Please follow ROS package conventions and keep changes focused.
