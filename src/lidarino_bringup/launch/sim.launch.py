import os
from pyexpat import model
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler, AppendEnvironmentVariable, DeclareLaunchArgument, TimerAction, EmitEvent
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    model_arg = DeclareLaunchArgument(
        'model',
        default_value='s2',
        choices=['v1', 's2'],
        description='Seleziona il modello del robot: v1, s2'
    )

    world_arg = DeclareLaunchArgument(
        'world',
        default_value='apartment.world',
        description='Seleziona il file del mondo Gazebo da caricare: lidarino.world, apartment.world'
    )

    model = LaunchConfiguration('model')
    world = LaunchConfiguration('world')
    pkg_share = FindPackageShare('lidarino_description')
    pkg_share_path = get_package_share_directory('lidarino_description')
    
    gazebo_models_path = os.path.join(pkg_share_path, '..')
    set_env = AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', gazebo_models_path)


    yaml_config_file = PathJoinSubstitution([
        FindPackageShare('lidarino_description'),
        'config',
        ['controllers_', model, '.yaml']
    ])
    world_file = PathJoinSubstitution([FindPackageShare('lidarino_description'), 'worlds', world])
    xacro_file = PathJoinSubstitution([pkg_share, 'urdf', ['lidarino_', model, '.urdf.xacro']])
    robot_xacro_cmd = Command(['xacro ', xacro_file, ' yaml_file:=', yaml_config_file, ' use_sim:=true'])
    robot_desc = ParameterValue(robot_xacro_cmd, value_type=str)

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True,
            'publish_frequency': 100.0
        }]
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')]),
        launch_arguments={
            'gz_args': ['-r ', world_file]
        }.items()
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-string', robot_xacro_cmd, 
            '-name', 'lidarino',
            '-allow_renaming', 'true',
            '-x', '-1.0',
            '-y', '3.5', 
            '-z', '0.05',
            '-Y', '3.14',    # ← Faccia verso sud
        ],
        output='screen'
    )

    # Bridge v1: solo ToF
    bridge_v1 = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        condition=IfCondition(PythonExpression(["'", model, "' == 'v1'"])),
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan_tof_1@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/scan_tof_2@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/scan_tof_3@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/scan_tof_4@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        ],
        output='screen'
    )

    # Bridge s2: solo Lidar
    bridge_s2 = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        condition=IfCondition(PythonExpression(["'", model, "' == 's2'"])),
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        ],
        output='screen'
    )

    bridge_camera = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # Immagine a colori RGB
            '/astra/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            # Immagine di profondità
            '/astra/camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
            # Nuvola di punti 3D (PointCloud)
            '/astra/camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            # Informazioni di calibrazione della camera
            '/astra/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        output='screen'
    )

    joint_state_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )
    
    tof_merger_node = Node(
        package='lidarino_description',
        executable='tof_merger',
        name='tof_merger',
        output='screen',
        condition=IfCondition(PythonExpression(["'", model, "' == 'v1'"])),
        parameters=[{'use_sim_time': True}]
    )

    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_controller", "--controller-manager", "/controller_manager"],
    )

    lidar_vel_spawner = Node(
        package="controller_manager",
        executable="spawner",
        condition=IfCondition(PythonExpression(["'", model, "' == 'v1'"])),
        arguments=["lidar_velocity_controller"],
    )

    delayed_spawners = TimerAction(
        period=5.0,
        actions=[
            joint_state_broadcaster,
            diff_drive_spawner,
            lidar_vel_spawner
        ]
    )

    navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('lidarino_bringup'), 'launch', 'navigation.launch.py'])
        ])
    )

    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('lidarino_bringup'), 'launch', 'slam.launch.py'])
        ])
    )

    bridge_imu = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU'
        ],
        output='screen'
    )

    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[
            PathJoinSubstitution([FindPackageShare('lidarino_description'), 'config', 'ekf.yaml']),
            {'use_sim_time': True}
        ],
        remappings=[
            ('odometry/filtered', 'odometry/filtered')  # lascia com'è, o personalizza
        ]
    )

    return LaunchDescription([
        model_arg,
        world_arg,
        set_env,
        rsp_node,
        gazebo,
        spawn_entity,
        bridge_v1,
        bridge_s2,
        bridge_camera,
        tof_merger_node,
        delayed_spawners,
        slam_launch,
        navigation_launch,
        bridge_imu,
        ekf_node,
    ])