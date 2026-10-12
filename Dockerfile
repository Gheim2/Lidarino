FROM ros:jazzy-ros-base

# Installa le dipendenze hardware ed elimina la cache di apt per mantenere l'immagine leggera
RUN apt-get update && apt-get install -y \
    nano \
    ros-jazzy-ros2-control \
    ros-jazzy-ros2-controllers \
    ros-jazzy-nav2-msgs \
    ros-jazzy-navigation2 \
    ros-jazzy-xacro \
    ros-jazzy-rmw-zenoh-cpp \
    ros-jazzy-camera-info-manager \
    ros-jazzy-image-publisher \
    ros-jazzy-image-geometry \
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-compressed-image-transport \
    ros-jazzy-cv-bridge \
    ros-jazzy-diagnostic-updater \
    ros-jazzy-diagnostic-msgs \
    ros-jazzy-statistics-msgs \
    ros-jazzy-backward-ros \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    alsa-utils \
    mbrola \
    mbrola-it3 \
    mbrola-it4 \
    libttspico-utils \
    libgflags-dev libgoogle-glog-dev libusb-1.0-0-dev libeigen3-dev libuvc-dev \
    libdw-dev \
    nlohmann-json3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    libudev-dev \
    git-lfs \
    unzip \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*



RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
