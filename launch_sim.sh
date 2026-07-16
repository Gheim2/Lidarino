#!/bin/bash
# ~/launch_sim.sh
source /opt/ros/jazzy/setup.bash
source ~/lidarino_ws/install/setup.bash

# Trap Ctrl+C per shutdown ordinato
trap 'echo "Shutting down..."; pkill -SIGINT -f "gz sim"; sleep 2; pkill -SIGTERM -f "ros2 launch"; exit 0' SIGINT

ros2 launch lidarino_description gazebo.launch.py "$@"
