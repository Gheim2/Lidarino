# Branch: `main` — Linux / Gazebo / Hardware Reale

Questo branch contiene il progetto Lidarino nella sua versione per **Linux (Ubuntu 24.04)**, con simulazione **Gazebo Harmonic** e supporto per il **robot fisico** tramite hardware interface ROS 2.

> Per la versione Windows + Isaac Sim, vedi il branch [`feature/isaac-sim`](../../tree/feature/isaac-sim).

---

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| OS | Ubuntu 24.04 |
| ROS 2 | Jazzy Jalisco |
| Simulatore | Gazebo Harmonic (SDF/`.world`) |
| Modello robot | URDF/Xacro + plugin Gazebo |
| LiDAR driver | `sllidar_ros2` |
| Hardware interface | `lidarino_hardware` (POSIX seriale) |
| Exploration | `explore_lite` (m-explore-ros2) |
| Middleware | DDS (default ROS 2) |
| Build | `colcon build` nativo |

---

## Struttura pacchetti

```
src/
├── lidarino_description/   # URDF, mesh, config, worlds Gazebo (.world)
├── lidarino_bringup/       # Launch: sim.launch.py, navigation, slam, robot
├── lidarino_hardware/      # Hardware interface ros2_control (POSIX)
├── sllidar_ros2/           # Driver RPLidar S2
└── m-explore-ros2/         # Esplorazione autonoma frontier-based
```

---

## Come buildare

```bash
# Installa le dipendenze
rosdep install --from-paths src --ignore-src -r -y

# Build
colcon build
source install/setup.bash
```

---

## Come avviare la simulazione

```bash
# Simulazione Gazebo con SLAM e Nav2
ros2 launch lidarino_bringup sim.launch.py world:=apartment.world

# Solo visualizzazione modello
ros2 launch lidarino_description display.launch.py
```

---

## Come avviare sul robot reale

```bash
# Avvia hardware interface + controller + EKF
ros2 launch lidarino_bringup robot.launch.py

# In un secondo terminale: navigazione
ros2 launch lidarino_bringup navigation.launch.py
```

---

## Regole di merge con `windows-isaac`

> ⚠️ **Non eseguire mai un merge completo** tra questo branch e `feature/isaac-sim`.  
> Le architetture sono incompatibili: POSIX vs Windows, Gazebo vs Isaac Sim, DDS vs Zenoh.

### ✅ File che possono essere cherry-picked verso `feature/isaac-sim`

| File / Cartella | Motivo |
|---|---|
| `urdf/meshes/*.stl` | Mesh identiche su entrambe le piattaforme |
| `urdf/lidarino_core_s2.xacro` | Struttura fisica del robot condivisa |
| `urdf/materials.xacro` | Materiali condivisi |
| `config/nav2_params.yaml` | Parametri Nav2 quasi identici |
| `config/ekf.yaml` | Configurazione EKF condivisa |
| `config/controllers_real.yaml` | Controller hardware condivisi |

### ❌ File che NON vanno mai cherry-picked verso `feature/isaac-sim`

| File / Cartella | Motivo |
|---|---|
| `worlds/*.world` | Formato Gazebo SDF, non supportato da Isaac |
| `urdf/lidarino_gazebo.xacro` | Plugin Gazebo, ignorati da Isaac |
| `urdf/lidarino_ros2_control.xacro` | Plugin gz_ros2_control, non usato su Isaac |
| `urdf/rplidars2.xacro` | Contiene sensor Gazebo |
| `urdf/astra_camera.xacro` | Contiene sensor Gazebo |
| `urdf/imu.xacro` | Contiene sensor Gazebo |
| `bringup/launch/sim.launch.py` | Specifico Gazebo |
| `lidarino_hardware/` | Dipendenze POSIX, non compila su Windows |
| `m-explore-ros2/` | Dipendenze POSIX, non compila su Windows |
| `sllidar_ros2/` | Dipendenze POSIX, non compila su Windows |

### Come fare cherry-pick dei file condivisi

```bash
# Esempio: aggiornare le mesh su feature/isaac-sim dopo averle modificate su main

# 1. Trova il commit hash
git log --oneline -- urdf/meshes/

# 2. Cherry-pick del singolo commit
git checkout feature/isaac-sim
git cherry-pick <hash> --no-commit

# 3. Rimuovi dallo staging i file che non vuoi
git restore --staged urdf/lidarino_gazebo.xacro  # esempio

# 4. Committa solo quello che serve
git commit -m "cherry-pick: update meshes from main"

# Oppure, se il commit è troppo mischiato, copia solo i file:
git checkout main -- urdf/meshes/
git commit -m "sync: update meshes from main"
```

---

## File specifici di questo branch

Questi file esistono **solo su `main`** e non devono mai apparire su `feature/isaac-sim`:

- `src/lidarino_hardware/` — hardware interface POSIX
- `src/sllidar_ros2/` — driver LiDAR Linux
- `src/m-explore-ros2/` — explore_lite
- `src/lidarino_description/worlds/*.world` — world Gazebo
- `launch_sim.sh` — script avvio Linux
