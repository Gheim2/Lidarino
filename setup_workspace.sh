#!/bin/bash
echo "Inizializzazione del workspace Lidarino..."

# 1. Scarica le dipendenze esterne
echo "Scaricamento delle repository esterne..."
vcs import src < lidarino.repos

# 2. Inserisce il blocco per il pacchetto non desiderato
echo "Esclusione di multirobot_map_merge..."
touch src/m-explore-ros2/map_merge/COLCON_IGNORE

# 3. Risolve le dipendenze di sistema
echo "Installazione delle dipendenze ROS 2..."
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy

echo "Setup completato! Ora puoi eseguire 'colcon build --symlink-install'"
