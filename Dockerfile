FROM ros:jazzy-ros-base

# Installa le dipendenze hardware ed elimina la cache di apt per mantenere l'immagine leggera
RUN apt-get update && apt-get install -y \
    nano \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    ros-jazzy-nav2-msgs \
    ros-jazzy-navigation2 \
    ros-jazzy-xacro \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
