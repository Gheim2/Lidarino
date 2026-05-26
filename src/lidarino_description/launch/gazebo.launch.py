import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, AppendEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.event_handlers import OnProcessExit
import xacro

def generate_launch_description():
    pkg_name = 'lidarino_description'
    pkg_share = get_package_share_directory(pkg_name)
    
    gazebo_models_path = os.path.join(pkg_share, '..')
    set_env = AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', gazebo_models_path)

    xacro_file = os.path.join(pkg_share, 'urdf', 'Lidarino.urdf.xacro')
    robot_desc = xacro.process_file(xacro_file).toxml()

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_desc, 'use_sim_time': True}]
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-topic', 'robot_description', '-name', 'lidarino'],
        output='screen'
    )

    # Il Ponte per l'Orologio e per i 4 sensori ToF
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan_tof_1@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/scan_tof_2@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/scan_tof_3@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/scan_tof_4@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
        ],
        output='screen'
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    velocity_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["lidar_velocity_controller", "--controller-manager", "/controller_manager"],
    )
    
    tof_merger_node = Node(
        package='lidarino_description',
        executable='tof_merger',
        name='tof_merger',
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    return LaunchDescription([
        set_env,
        rsp_node,
        gazebo,
        spawn_entity,
        bridge_node,
        tof_merger_node,
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[joint_state_broadcaster, velocity_controller],
            )
        ),
    ])