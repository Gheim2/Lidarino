import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    # Nome del pacchetto
    pkg_name = 'lidarino_description'
    
    # Trova la cartella 'share' del pacchetto installato
    pkg_share = get_package_share_directory(pkg_name)
    
    # Percorso assoluto del file Xacro
    xacro_file = os.path.join(pkg_share, 'urdf', 'Lidarino.urdf.xacro')
    
    # Compila il file Xacro in XML (URDF) dinamicamente
    doc = xacro.process_file(xacro_file)
    robot_desc = doc.toxml()

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
        output='screen'
    )

    # Ritorna e avvia tutti i nodi contemporaneamente
    return LaunchDescription([
        rsp_node,
        jsp_gui_node,
        rviz_node
    ])