# Lidarino

Lidarino is a small differential-drive (unicycle) robot running ROS 2 Jazzy. This repository contains the ROS 2 side: the robot model, the `ros2_control` hardware interface that talks to the motor controller, and the launch files for the real robot and the Gazebo simulation.

The low-level firmware (motors, encoders, IMU, battery) lives in a separate repository, **Lidarino-firmware** (PlatformIO, ESP32-S3). The two must stay in sync: see [Firmware interface](#firmware-interface).

> Branches: `main` is the Linux version (real robot + Gazebo). `feature/isaac-sim` is the Windows + Isaac Sim version. Never merge the two branches: see `BRANCH.md` for which files can be shared.

## Contents

- [System overview](#system-overview)
- [Hardware](#hardware)
- [Repository layout](#repository-layout)
- [Setup](#setup)
- [Running the real robot](#running-the-real-robot)
- [Driving the robot](#driving-the-robot)
- [Viewing the robot from a PC](#viewing-the-robot-from-a-pc)
- [Topics and frames](#topics-and-frames)
- [Firmware interface](#firmware-interface)
- [Hardware interface behavior and log messages](#hardware-interface-behavior-and-log-messages)
- [Configuration files](#configuration-files)
- [Utility scripts](#utility-scripts)
- [Simulation (Gazebo)](#simulation-gazebo)
- [Development workflow](#development-workflow)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)

## System overview

```
 Windows PC (development)                Orange Pi 4 Pro (on the robot)
 ┌───────────────────────────┐   LAN   ┌──────────────────────────────────────────┐
 │ edit code, RViz2, ros2 CLI │◄──────►│ Docker container "lidarino_robot"        │
 │ pixi env, rmw_zenoh        │  Zenoh │  ROS 2 Jazzy, rmw_zenoh, Zenoh router    │
 └───────────────────────────┘         │  robot_state_publisher                   │
                                       │  ros2_control_node                       │
                                       │   └ lidarino_hardware (serial plugin)    │
                                       │  controllers: diff_drive, joint_state,   │
                                       │               imu_broadcaster            │
                                       │  sllidar_node (RPLIDAR S2)               │
                                       └───────┬───────────────────────┬──────────┘
                                               │ USB serial            │ USB serial
                                               │ /dev/lidarino         │ /dev/ttyUSB0
                                       ┌───────▼──────────┐    ┌───────▼────────┐
                                       │ ESP32-S3 firmware │    │ RPLIDAR S2     │
                                       │ PID, encoders,    │    └────────────────┘
                                       │ IMU, battery      │
                                       └───────┬──────────┘
                                               │
                                     TB6612FNG ─ 2 DC motors
```

- The **Orange Pi** runs all ROS 2 software inside a Docker container. ROS 2 nodes communicate through **Zenoh** (`rmw_zenoh_cpp`), which needs a Zenoh router running.
- The **ESP32-S3** runs the wheel speed PID at 100 Hz and exchanges binary packets with the hardware interface: wheel velocity commands in, encoder positions, IMU and battery out (50 Hz).
- The **Windows PC** is used to edit code and to look at the robot (RViz2, ros2 CLI) over the network. Nothing is built for the robot on the PC.

## Hardware

| Part | Model | Connection |
|---|---|---|
| Main computer | Orange Pi 4 Pro, Ubuntu | - |
| Motor controller | BPI-Leaf-S3 (ESP32-S3) | native USB, `/dev/lidarino` |
| Motor driver | TB6612FNG | ESP32 GPIO |
| Wheel encoders | 2 × AS5600 (4096 ticks per turn) | ESP32 I2C |
| IMU | MPU6500 | ESP32 I2C |
| LiDAR | RPLIDAR S2 | USB, `/dev/ttyUSB0` |
| Camera | ORBBEC Astra Pro | USB (driver not started yet) |
| Battery | 3S LiPo (9-12.6 V) | ESP32 ADC through a divider |

Robot geometry used by the controller: wheel radius 0.0325 m, wheel separation 0.128 m.

Pinout, wiring notes, LED colors and the IMU calibration are documented in the firmware README.

## Repository layout

```
lidarino_repo/
├── src/
│   ├── lidarino_bringup/        launch files (real robot, simulation, SLAM, navigation)
│   ├── lidarino_description/    URDF/Xacro, meshes, config YAML, Gazebo worlds
│   └── lidarino_hardware/       ros2_control hardware interface (C++) + utility scripts
├── lidarino.repos               third-party packages, imported with vcs
├── setup_workspace.sh           first-time workspace setup (vcs import + rosdep)
├── Dockerfile                   ROS 2 Jazzy image used on the Orange Pi
├── docker-compose.yml           container "lidarino_robot"
├── sync_to_pi.sh                rsync of this repo from the PC to the Orange Pi
├── ros_manager.py               text menu for the simulation (build, Gazebo, RViz, teleop, explore)
├── launch_sim.sh                Gazebo launcher used by ros_manager.py
└── BRANCH.md                    rules for the main / feature/isaac-sim branches
```

### Packages

**`lidarino_hardware`** (C++, `ament_cmake`)
- `LidarinoSystemHardware`: a `ros2_control` `SystemInterface` plugin. It opens the serial port, sends wheel velocity commands, parses telemetry and exposes:
  - command interfaces: `L_wheel_Revolute/velocity`, `R_wheel_Revolute/velocity` (rad/s);
  - state interfaces: wheel `position` (rad) and `velocity` (rad/s), `imu_sensor` (orientation, linear acceleration, angular velocity), `battery_sensor/voltage`.
- Publishes `/battery_voltage` and `/battery_status` at 1 Hz.
- Scripts `imu_covariance.py` and `battery_speaker.py` (see [Utility scripts](#utility-scripts)).

**`lidarino_description`** (Python, `ament_python`)
- `urdf/lidarino_s2.urdf.xacro`: entry point of the current robot (S2 lidar). It includes the chassis (`lidarino_core_s2.xacro`), the sensors (`rplidars2.xacro`, `astra_camera.xacro`, `imu.xacro`), the Gazebo plugins (`lidarino_gazebo.xacro`) and the `ros2_control` block (`lidarino_ros2_control.xacro`, which loads the Gazebo plugin or `lidarino_hardware` depending on `use_sim`).
- `*_v1.*` files and `tof_merger`: the old v1 robot (rotating ToF sensors), only used in simulation with `model:=v1`.
- `config/`: controllers, EKF, lidar, SLAM, Nav2 and exploration parameters.
- `worlds/`: Gazebo worlds (`apartment.world`, `lidarino.world`).
- `launch/display.launch.py`: shows the model in RViz2 with a joint slider GUI.

**`lidarino_bringup`** (`ament_cmake`, launch only)
- `robot.launch.py`: real robot.
- `sim.launch.py`: Gazebo simulation with SLAM and Nav2.
- `slam.launch.py`: `slam_toolbox` (online async).
- `navigation.launch.py`: Nav2 and a relay from `/cmd_vel` to `/diff_drive_controller/cmd_vel`.

### Third-party packages (`lidarino.repos`)

Imported in `src/` by `setup_workspace.sh` and ignored by git:

- `sllidar_ros2`: RPLIDAR S2 driver.
- `m-explore-ros2`: frontier exploration (`explore_lite`). Its `map_merge` package is disabled with `COLCON_IGNORE`.
- `ros2_astra_camera`: ORBBEC Astra driver.

## Setup

### Orange Pi (robot)

1. **Workspace**: this repository is the workspace root, at `/home/orangepi/lidarino_ws`.

2. **Container**: build and start it once; it restarts automatically.
   ```bash
   cd ~/lidarino_ws
   docker compose up -d --build
   docker exec -it lidarino_robot bash
   ```
   The container uses the host network, runs privileged with `/dev` mounted (serial devices), and mounts the workspace as `/root/lidarino_ws`. `RMW_IMPLEMENTATION=rmw_zenoh_cpp` is set in `docker-compose.yml`.

3. **Third-party packages and dependencies** (inside the container, once):
   ```bash
   cd /root/lidarino_ws
   ./setup_workspace.sh
   ```

4. **Build** (inside the container):
   ```bash
   colcon build --symlink-install --parallel-workers 2
   source install/setup.bash
   ```

5. **udev rule for the ESP32** (on the Orange Pi host, once). It creates `/dev/lidarino`. The firmware uses the ESP32-S3 USB-Serial/JTAG port, USB ID `303a:1001`; older TinyUSB firmware used `303a:80df`, so both are listed:
   ```
   # /etc/udev/rules.d/99-lidarino.rules
   ACTION=="add", KERNEL=="ttyACM[0-9]*", SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="80df", SYMLINK+="lidarino", MODE="0666"
   ACTION=="add", KERNEL=="ttyACM[0-9]*", SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="1001", SYMLINK+="lidarino", MODE="0666"
   ```
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger --subsystem-match=tty
   ls -l /dev/lidarino
   ```

6. **Zenoh router**: every ROS 2 terminal needs a router. Start one in the container and leave it running:
   ```bash
   ros2 run rmw_zenoh_cpp rmw_zenohd
   ```

### Windows PC (development)

- Edit the code in this repository and copy it to the Pi with `sync_to_pi.sh` (see [Development workflow](#development-workflow)).
- To use `ros2` and RViz2 against the robot, use the pixi environment of the `jazzy_ws` workspace (it provides ROS 2 Jazzy and `rmw_zenoh_cpp` on Windows). The PC must reach the Zenoh router on the Pi, for example by connecting to it directly:
  ```powershell
  $env:ZENOH_CONFIG_OVERRIDE = 'connect/endpoints=["tcp/<pi-ip>:7447"]'
  pixi run rviz2
  ```

## Running the real robot

Inside the container, with the Zenoh router running:

```bash
source /root/lidarino_ws/install/setup.bash
ros2 launch lidarino_bringup robot.launch.py
```

It starts:

- `robot_state_publisher` with the URDF (`use_sim:=false`);
- `ros2_control_node` with `lidarino_hardware` on `/dev/lidarino` and the controllers `joint_state_broadcaster`, `diff_drive_controller`, `imu_broadcaster`;
- `sllidar_node` for the RPLIDAR S2 (parameters in `config/sllidar_s2.yaml`);
- optionally the EKF (`robot_localization`).

| Argument | Default | Effect |
|---|---|---|
| `use_lidar` | `true` | Start the RPLIDAR S2 driver |
| `use_ekf` | `false` | Start the EKF. When `true`, the EKF publishes `odom → base_link` and the diff drive controller stops publishing it (`config/diff_drive_no_odom_tf.yaml`) |

Example: `ros2 launch lidarino_bringup robot.launch.py use_ekf:=true`.

**Before launching**, make sure:

- the ESP32 runs the firmware with `DEBUG_MODE 0`. With the debug firmware, the binary command bytes are read as debug keys;
- nothing else uses `/dev/lidarino` (for example a serial monitor or a firmware upload);
- the robot is on a stand or in a free area: the robot launch accepts velocity commands as soon as it starts.

## Driving the robot

`diff_drive_controller` (Jazzy) only accepts **`geometry_msgs/msg/TwistStamped`** on `/diff_drive_controller/cmd_vel`. If no command arrives for 0.5 s, it brakes and logs `Velocity command timed out. Braking.`: that is normal when nobody is driving.

Constant speed from the command line (publish continuously, Ctrl+C to stop):

```bash
ros2 topic pub -r 10 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.05}, angular: {z: 0.0}}}"
```

A zero timestamp is fine: the controller replaces it with the current time and logs it once.

Keyboard:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p stamped:=true -p frame_id:=base_link -r cmd_vel:=/diff_drive_controller/cmd_vel
```

For the first tests, keep the wheels off the ground and use low speeds (0.05 m/s ≈ 1.5 rad/s at the wheel).

## Viewing the robot from a PC

In RViz2 set **Fixed Frame** to `odom` and add:

- `RobotModel` (topic `/robot_description`);
- `LaserScan` on `/scan`;
- `TF` to check the frame tree;
- `Odometry` on `/diff_drive_controller/odom`.

To see only the lidar, `base_link` also works as fixed frame: it only needs `robot_state_publisher` and the lidar.

## Topics and frames

### Main topics

| Topic | Type | Publisher | Notes |
|---|---|---|---|
| `/diff_drive_controller/cmd_vel` | `TwistStamped` | you / Nav2 relay | velocity command |
| `/diff_drive_controller/odom` | `Odometry` | diff_drive_controller | wheel odometry, 50 Hz |
| `/joint_states` | `JointState` | joint_state_broadcaster | wheel positions and velocities |
| `/imu_broadcaster/imu` | `Imu` | imu_broadcaster | acceleration and angular velocity in `imu_link`, no orientation |
| `/scan` | `LaserScan` | sllidar_node | frame `rplidars2_laser_link` |
| `/battery_voltage` | `Float32` | lidarino_hardware | V, 1 Hz |
| `/battery_status` | `BatteryState` | lidarino_hardware | voltage and percentage (9.0-12.6 V), 1 Hz |
| `/odometry/filtered` | `Odometry` | EKF | only with `use_ekf:=true` |
| `/robot_description` | `String` | robot_state_publisher | URDF |

### TF tree

```
odom ──► base_link ──► rplidars2_link ──► rplidars2_laser_link
 │            ├──► imu_link
 │            ├──► astra_link ──► astra_optical_frame
 │            ├──► wheel_L, wheel_R  (from /joint_states)
 │            └──► caster, body_lid
 └ published by diff_drive_controller, or by the EKF with use_ekf:=true
```

`map → odom` is published by `slam_toolbox` when SLAM runs.

## Firmware interface

The hardware interface and the firmware share a binary protocol over USB serial. The reference definition is `include/serial_protocol.h` in the firmware repository; the ROS 2 copy is in `src/lidarino_hardware/include/lidarino_hardware/lidarino_hardware.hpp`. **Any change must be applied to both sides.**

- Port `/dev/lidarino`, 115200 baud, raw mode (`cfmakeraw`, so `0x0D` is not translated).
- Packets are packed, little-endian, start with `0xAA 0x55` and end with `0x0D`. Checksum: XOR of all bytes before the checksum, sync bytes included.
- **Command** (Orange Pi → ESP32, 10 bytes): `vel_left`, `vel_right` as int16 in rad/s × 1000, `reserved` (0). Sent at every `ros2_control` cycle (100 Hz). The firmware stops the wheels if no valid command arrives for 500 ms.
- **Telemetry** (ESP32 → Orange Pi, 27 bytes, 50 Hz): `pos_left`, `pos_right` as int32 encoder ticks (4096 per turn), accelerations (m/s² × 1000) and angular velocities (rad/s × 1000) as int16 in the robot frame, `status_flags` (bit 0 e-stop, bit 1 left encoder OK, bit 2 right encoder OK, bit 3 IMU OK), `battery_mv` as uint16.
- Units follow REP 103 (meters, radians, seconds). All conversions are done in the firmware, except ticks → radians and the × 1000 scaling, done in the hardware interface.

## Hardware interface behavior and log messages

- **Reconnection**: if the ESP32 resets, the USB port disappears. The interface closes the port, retries once per second and continues; wheel positions continue from where they were, so odometry does not jump.
- **Non-blocking**: reads and writes never block the `ros2_control` loop. Commands that cannot be written (output buffer full) are skipped and counted.
- **Text from the ESP32**: printable lines in the serial stream (boot report, setup errors) are written to the log as `ESP32: ...`.

| Log message | Meaning | What to do |
|---|---|---|
| `Velocity command timed out. Braking.` (diff_drive_controller) | no command on `cmd_vel` for 0.5 s | normal when not driving |
| `Nessuna telemetria valida dall'ESP32 da N s su /dev/lidarino` | no valid packet for more than 2 s | ESP32 stuck in setup, debug firmware, or wrong port. Check the ESP32 LED |
| `Serial write: X/Y comandi saltati negli ultimi 2 s` | X of Y commands could not be sent | X = Y: the ESP32 is not reading at all; small X: occasional delays |
| `ESP32: [BOOT] reset_reason=... last_stage=... gyro_bias=...` | ESP32 (re)started | `reset_reason` and `last_stage` explain a watchdog or panic reset |
| `ESP32: Error initializing ...` | firmware setup problem (encoder, IMU, motor PWM) | check the wiring of that part |
| `ESP32 riporta IMU non funzionante` | IMU OK bit is 0 | IMU disconnected; the robot still drives on encoders |
| `Telemetry checksum mismatch` | corrupted packet | occasional is fine; continuous means a protocol mismatch with the firmware |
| `Porta seriale persa (...)` / `Porta seriale ... riaperta` | USB port lost and reopened | ESP32 reset or USB cable |

## Configuration files

All in `src/lidarino_description/config/`:

| File | Used by | Content |
|---|---|---|
| `controllers_real.yaml` | real robot | controller manager (100 Hz), diff drive (wheel geometry, odometry covariances), IMU broadcaster (measured covariances) |
| `diff_drive_no_odom_tf.yaml` | real robot, `use_ekf:=true` | disables the controller's `odom → base_link` TF |
| `sllidar_s2.yaml` | real robot | RPLIDAR S2 port, baud rate, `frame_id: rplidars2_laser_link`, scan mode |
| `ekf.yaml` | real robot and simulation | EKF fusing wheel odometry velocities and the IMU yaw rate; publishes `odom → base_link` |
| `controllers_s2.yaml`, `controllers_v1.yaml` | simulation | controllers for Gazebo |
| `mapper_params_s2.yaml`, `mapper_params_v1.yaml` | SLAM | `slam_toolbox` parameters |
| `nav2_params.yaml` | navigation | Nav2 parameters |
| `explore.yaml` | exploration | `explore_lite` parameters |
| `justRobot.rviz` | `display.launch.py` | RViz2 configuration |

The serial port of the ESP32 (`/dev/lidarino`) and the wheel joint names are set in `urdf/lidarino_ros2_control.xacro`.

## Utility scripts

Installed by `lidarino_hardware`, run inside the container with the robot launch running:

- **`imu_covariance.py`**: collects 1000 IMU samples (about 20 s) from `/imu_broadcaster/imu` and prints mean and covariance. Used to fill the IMU covariances in `controllers_real.yaml`. Keep the robot still with the motors off.
  ```bash
  ros2 run lidarino_hardware imu_covariance.py
  ```
- **`battery_speaker.py`**: subscribes to `/battery_voltage` and says the battery level aloud in Italian (`pico2wave` + `aplay`). Parameters: `alsa_device` (default `plughw:1,0`), `v_empty` (10.0 V), `v_full` (12.6 V), `sample_duration_s` (3 s).
  ```bash
  ros2 run lidarino_hardware battery_speaker.py
  ```

The IMU calibration itself (offset, scale, alignment) is done in the firmware, with `tools/imu_calibrate.py` from the firmware repository.

## Simulation (Gazebo)

On a Linux PC with ROS 2 Jazzy and Gazebo Harmonic:

```bash
ros2 launch lidarino_bringup sim.launch.py world:=apartment.world   # model:=s2 (default) or v1
```

It starts Gazebo, spawns the robot, the controllers, the bridges, the EKF, SLAM and Nav2. `python3 ros_manager.py` offers a menu for the common actions (build, Gazebo, RViz2, keyboard teleop, autonomous exploration).

To only look at the model: `ros2 launch lidarino_description display.launch.py`.

## Development workflow

1. Edit the code on the PC.
2. Copy it to the Pi from Git Bash, always checking the preview first:
   ```bash
   ./sync_to_pi.sh --dry-run
   ./sync_to_pi.sh             # --delete also removes files deleted locally (asks first)
   ```
   The target host comes from `LIDARINO_HOST` (an SSH host in `~/.ssh/config`), for example `LIDARINO_HOST=orangepi ./sync_to_pi.sh`. The script never copies `build/`, `install/`, `log/`, `.git/`, meshes (`*.stl`) or files ignored by git, and refuses files with CRLF line endings (the repository uses LF).
3. Rebuild in the container: `colcon build --symlink-install --packages-select <changed packages>`.
4. Commit and push from the PC only. Do not `git pull` on the Pi: it would conflict with the files copied by rsync.

## Troubleshooting

**RViz2 shows no laser points / "no valid fixed frame"**
The scan frame must exist in the TF tree. `robot.launch.py` starts the lidar with `frame_id: rplidars2_laser_link`. The stock `sllidar_s2_launch.py` uses `laser`, which is not in the URDF. Use `odom` (or `base_link`) as fixed frame.

**`Nessuna telemetria valida` and all commands skipped**
The ESP32 is not running its main loop or is not sending. Check its LED (see the firmware README): solid blue means stuck in setup, the log shows `ESP32: Error initializing ...`. Also check that the firmware was built with `DEBUG_MODE 0`.

**Commands accepted but the wheels do not move**
Check where the chain stops. `ros2 topic echo /controller_manager/introspection_data/full` shows the value written to `command_interface.*_wheel_Revolute/velocity`; `/joint_states` shows whether the encoders move. If commands reach the ESP32 (green LED) but the wheels stay still, the problem is in the firmware or the motor wiring (driver logic supply, PWM). The firmware README has a PWM test.

**`/dev/lidarino` missing**
Check `lsusb | grep 303a` and the udev rule (both USB IDs must be listed).

## Known limitations

- `navigation.launch.py` sets `use_sim_time: true`, and `slam.launch.py` defaults to `use_sim_time:=true` (as does `mapper_params_s2.yaml`): they are written for the simulation. On the real robot they need `use_sim_time` set to `false`.
- The Astra Pro camera driver is imported but not started by `robot.launch.py`.
- The IMU gives no orientation: the EKF only uses its angular velocity.
