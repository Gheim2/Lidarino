import os
from pyexpat import model
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, AppendEnvironmentVariable, DeclareLaunchArgument, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    model_arg = DeclareLaunchArgument(
        'model',
        default_value='s2',
        choices=['v1', 's2'],
        description='Seleziona il modello per caricare i parametri SLAM corretti'
    )
    model = LaunchConfiguration('model')
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Usa il tempo di simulazione fornito da Gazebo'
    )
    use_sim_time = LaunchConfiguration('use_sim_time')

    # 2. Costruzione dinamica del percorso al file YAML
    # Risolverà in: config/mapper_params_s2.yaml o config/mapper_params_v1.yaml
    slam_params_file = PathJoinSubstitution([
        FindPackageShare('lidarino_description'),
        'config',
        ['mapper_params_', model, '.yaml']
    ])

    slam_toolbox_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('slam_toolbox'),
                'launch',
                'online_async_launch.py'
            ])
        ]),
        launch_arguments={
            'slam_params_file': slam_params_file,
            'use_sim_time': use_sim_time
        }.items()
    )

    return LaunchDescription([
        model_arg,
        use_sim_time_arg,
        slam_toolbox_launch
    ])