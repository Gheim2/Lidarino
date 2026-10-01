import os
from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessStart
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    # I file urdf sono dentro lidarino_description/urdf
    pkg_description = FindPackageShare('lidarino_description')
    xacro_file = PathJoinSubstitution([pkg_description, 'urdf', 'lidarino_s2.urdf.xacro'])
    controllers_file = PathJoinSubstitution([pkg_description, 'config', 'controllers_real.yaml'])
    robot_xacro_cmd = Command(['xacro ', xacro_file, ' yaml_file:=', controllers_file, ' use_sim:=false'])
    robot_description = {'robot_description': ParameterValue(robot_xacro_cmd, value_type=str)}

    # Nodo Robot State Publisher (pubblica le TF fisse in base all'URDF)
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description]
    )
    
    # Controller manager
    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[controllers_file],
	remappings=[
		('~/robot_description', '/robot_description')
        ],
        output='screen'
    )

    # Lettura encoder
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
    )

    # Movimento motori
    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
    )

    imu_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['imu_broadcaster', '--controller-manager', '/controller_manager'],
    )

    # Spawner dopo il controller_manager
    delay_joint_state_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[joint_state_broadcaster_spawner],
        )
    )

    delay_diff_drive_controller_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[diff_drive_controller_spawner],
        )
    )

    delay_imu_broadcaster_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[imu_broadcaster_spawner],
        )
    )

    return LaunchDescription([
        node_robot_state_publisher,
        controller_manager,
        delay_joint_state_broadcaster_spawner,
        delay_diff_drive_controller_spawner,
        delay_imu_broadcaster_spawner
    ])
