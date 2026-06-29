import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_share = FindPackageShare('lidarino_description')

    model_arg = DeclareLaunchArgument(
        'model',
        default_value='s2',
        choices=['v1', 's2'],
        description='Seleziona il modello del robot: v1, s2'
    )
    model = LaunchConfiguration('model')
    xacro_file = PathJoinSubstitution([
        pkg_share,
        'urdf',
        ['lidarino_', model, '.urdf.xacro']
    ])

    pkg_share_dir = get_package_share_directory('lidarino_description')
    rviz_config_file = os.path.join(pkg_share_dir, 'config', 'justRobot.rviz')

    robot_desc = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
    # Nodo 1: Robot State Publisher (Invia il modello URDF a tutto il sistema)
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}]
    )

    # Nodo 2: Joint State Publisher GUI (Mostra la finestrella con gli slider per le ruote)
    jsp_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        output='screen'
    )

    # Nodo 3: Rviz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file]
    )

    # Ritorna e avvia tutti i nodi contemporaneamente
    return LaunchDescription([
        model_arg,
        rsp_node,
        jsp_gui_node,
        rviz_node
    ])