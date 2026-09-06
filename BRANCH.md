# Branch: `feature/isaac-sim` — Windows / Isaac Sim

Questo branch contiene il progetto Lidarino nella sua versione per **Windows 11**, con simulazione **NVIDIA Isaac Sim** e integrazione ROS 2 tramite **Zenoh**.

> Per la versione Linux + Gazebo + hardware reale, vedi il branch [`main`](../../tree/main).

---

## Stack tecnologico

| Componente | Tecnologia |
|---|---|
| OS | Windows 11 |
| ROS 2 | Jazzy Jalisco (via Pixi/RoboStack) |
| Simulatore | NVIDIA Isaac Sim 6.x (USD) |
| Modello robot | URDF/Xacro (no plugin Gazebo) + USD |
| LiDAR | OmniGraph Isaac Sim (RTX Lidar) |
| Hardware interface | OmniGraph Differential Controller |
| Exploration | Nodo Python frontier-based (Windows-compatible) |
| Middleware | Zenoh (`rmw_zenoh_cpp`) |
| Build | `colcon build` via Pixi shell |

---

## Struttura pacchetti

```
src/
├── lidarino_description/   # URDF, mesh, config, USD, worlds Isaac
│   ├── urdf/
│   │   ├── lidarino_isaac.urdf.xacro   # xacro Isaac Sim
│   │   └── meshes/                     # STL condivisi con main
│   ├── usd/                            # Modelli Isaac Sim (.usd, .usda)
│   ├── worlds/                         # World Isaac (.usd)
│   └── config/                         # nav2_params, ekf, controllers
├── lidarino_bringup/       # Launch: isaac.launch.py, navigation, slam
└── lidarino_explore/       # Esplorazione autonoma (Python, Windows-compatible)
```

### Pacchetti con COLCON_IGNORE (non buildano su Windows)

```
src/lidarino_hardware/   ← COLCON_IGNORE (POSIX seriale)
src/sllidar_ros2/        ← COLCON_IGNORE (POSIX seriale)
src/m-explore-ros2/explore/  ← COLCON_IGNORE (dipendenze POSIX)
```

---

## Prerequisiti

1. **NVIDIA Isaac Sim 6.x** installato
2. **Pixi** installato (`winget install prefix-dev.pixi`)
3. **Workspace Pixi** configurato con ROS 2 Jazzy e Zenoh

---

## Come buildare

```powershell
# Entra nell'ambiente Pixi
pixi shell

# Build (esclude automaticamente i pacchetti con COLCON_IGNORE)
colcon build
source install/setup.ps1  # oppure: . install/setup.ps1
```

---

## Come avviare

```powershell
# Step 1: avvia l'ambiente completo (Zenoh + Isaac Sim + terminale ROS2)
.\start_env.bat

# Step 2: nel terminale ROS2 che si apre, avvia il launch file Isaac
ros2 launch lidarino_bringup isaac.launch.py

# Step 3: in Isaac Sim, premi Play per avviare la simulazione
```

---

## Architettura Isaac Sim

I sensori e i motori sono gestiti tramite **OmniGraph** direttamente in Isaac Sim, senza hardware interface ROS 2:

```
Isaac Sim OmniGraph
├── Action Graph 1: Clock        → /clock
├── Action Graph 2: Drive + Odom → /cmd_vel (sub), /odom (pub), TF odom→base_link
├── Action Graph 3: LiDAR        → /scan
├── Action Graph 4: IMU          → /imu
├── Action Graph 5: Camera       → /astra/camera/*
└── Action Graph 6: Joint States → /joint_states
```

Il launch file `isaac.launch.py` avvia solo i nodi ROS 2 (RSP, EKF, SLAM, Nav2) — Isaac Sim gestisce autonomamente fisica e sensori.

---

## Regole di merge con `main`

> ⚠️ **Non eseguire mai un merge completo** tra questo branch e `main`.  
> Le architetture sono incompatibili: Windows vs POSIX, Isaac vs Gazebo, Zenoh vs DDS.

### ✅ File che possono essere ricevuti da `main` via cherry-pick

| File / Cartella | Motivo |
|---|---|
| `urdf/meshes/*.stl` | Mesh identiche su entrambe le piattaforme |
| `urdf/lidarino_core_s2.xacro` | Struttura fisica del robot condivisa |
| `urdf/materials.xacro` | Materiali condivisi |
| `config/nav2_params.yaml` | Parametri Nav2 quasi identici |
| `config/ekf.yaml` | Configurazione EKF condivisa |
| `config/controllers_real.yaml` | Controller hardware condivisi |

### ❌ File che NON vanno mai ricevuti da `main`

| File / Cartella | Motivo |
|---|---|
| `urdf/lidarino_s2.urdf.xacro` | Contiene plugin Gazebo |
| `urdf/lidarino_gazebo.xacro` | Plugin Gazebo incompatibili |
| `urdf/lidarino_ros2_control.xacro` | Plugin gz_ros2_control |
| `urdf/rplidars2.xacro` | Sensor Gazebo |
| `urdf/astra_camera.xacro` | Sensor Gazebo |
| `urdf/imu.xacro` | Sensor Gazebo |
| `worlds/*.world` | Formato SDF Gazebo |
| `bringup/launch/sim.launch.py` | Specifico Gazebo |
| Tutto `lidarino_hardware/` | Non compila su Windows |
| Tutto `sllidar_ros2/` | Non compila su Windows |
| Tutto `m-explore-ros2/` | Non compila su Windows |

### Come ricevere aggiornamenti da `main`

```powershell
# Esempio: ricevere mesh aggiornate da main

# Opzione A: cherry-pick selettivo
git checkout feature/isaac-sim
git cherry-pick <hash> --no-commit
# Rimuovi dallo staging i file indesiderati, poi committa

# Opzione B: copia diretta dei file (più sicura se il commit è mischiato)
git checkout main -- src/lidarino_description/urdf/meshes/
git commit -m "sync: update meshes from main"
```

---

## File specifici di questo branch

Questi file esistono **solo su `feature/isaac-sim`** e non devono mai apparire su `main`:

- `src/lidarino_description/usd/` — modelli Isaac Sim
- `src/lidarino_description/urdf/lidarino_isaac.urdf.xacro` — xacro senza Gazebo
- `src/lidarino_description/urdf/lidarino_isaac.urdf` — URDF generato per Isaac
- `src/lidarino_description/worlds/StageIsaac.usd` — world Isaac
- `src/lidarino_bringup/launch/isaac.launch.py` — launch Isaac Sim
- `src/lidarino_explore/` — nodo Python esplorazione Windows-compatible
- `start_env.bat` — script avvio Windows
- `.env.example` — template configurazione path Windows
- `pixi.toml` — configurazione ambiente Pixi