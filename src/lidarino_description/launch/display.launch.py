import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_share = FindPackageShare('lidarino_description')

    variant_arg = DeclareLaunchArgument(
        'variant',
        default_value='isaac',
        choices=['v1', 's2', 'isaac'],
        description='Variante URDF: s2 (Gazebo), v1 (Gazebo), isaac (Isaac Sim)'
    )
    variant = LaunchConfiguration('variant')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    xacro_file = PathJoinSubstitution([
        pkg_share,
        'urdf',
        ['lidarino_', variant, '.urdf.xacro']
    ])


    pkg_share_dir = get_package_share_directory('lidarino_description')
    rviz_config_file = os.path.join(pkg_share_dir, 'config', 'justRobot.rviz')

    robot_desc = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)
    # Nodo 1: Robot State Publisher (Invia il modello URDF a tutto il sistema)
    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}, {'use_sim_time': use_sim_time}]
    )

    # Nodo 2: Rviz2
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=['-d', rviz_config_file]
    )

    delayed_rviz = TimerAction(
        period=3.0,
        actions=[rviz_node]  # Avvia Rviz2 dopo 3 secondi
    )

    # Ritorna e avvia tutti i nodi contemporaneamente
    return LaunchDescription([
        variant_arg,
        rsp_node,
        delayed_rviz,
    ])