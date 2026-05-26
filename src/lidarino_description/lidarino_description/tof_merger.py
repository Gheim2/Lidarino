#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, JointState
from rclpy.qos import qos_profile_sensor_data
import math

class TofMerger(Node):
    def __init__(self):
        super().__init__('tof_merger')
        
        # Il publisher del LiDAR fuso a 360 gradi
        self.publisher_ = self.create_publisher(LaserScan, '/scan', qos_profile_sensor_data)
        
        # Sottoscrizioni ai 6 ToF
        self.create_subscription(LaserScan, '/scan_tof_1', lambda msg: self.tof_cb(msg, 0.0), qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan_tof_2', lambda msg: self.tof_cb(msg, math.pi / 2.0), qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan_tof_3', lambda msg: self.tof_cb(msg, math.pi), qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan_tof_4', lambda msg: self.tof_cb(msg, -math.pi / 2.0), qos_profile_sensor_data)
        
        # Sottoscrizione per leggere l'encoder del motore
        self.create_subscription(JointState, '/joint_states', self.joint_cb, 10)
        self.current_lidar_angle = 0.0
        # Dizionario per memorizzare le ultime letture
        self.scan_buffer = [float('inf')] * 360
        # Timer a 10Hz per pubblicare il pacchetto fuso
        self.timer = self.create_timer(0.1, self.publish_merged_scan)

    def joint_cb(self, msg):
        try:
            idx = msg.name.index('lidar_Revolute')
            self.current_lidar_angle = msg.position[idx]
        except ValueError:
            pass

    def get_min_distance(self, msg):
        """Simula l'hardware del VL54L0X prendendo l'oggetto più vicino nel FOV"""
        valid_ranges = [r for r in msg.ranges if 0.05 < r < 2.0]
        if valid_ranges:
            return min(valid_ranges)
        return float('inf')
    
    # Callback dei sensori: aggiornano l'ultima distanza letta
    def tof_cb(self, msg, offset_rad):
        distance = self.get_min_distance(msg)
        global_angle = -(self.current_lidar_angle + offset_rad)
        # Angolo normalizzato convertito in indice da 0 a 359
        idx = int((global_angle + math.pi) * 180.0 / math.pi) % 360
        self.scan_buffer[idx] = distance

    def publish_merged_scan(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        # Frame nel telaio
        msg.header.frame_id = 'base_link' 
        
        # Creiamo un LiDAR a 360 gradi, risoluzione 1 grado
        msg.angle_increment = math.pi / 180.0 # 1 grado in radianti
        msg.angle_min = -math.pi
        msg.angle_max = math.pi - msg.angle_increment
        msg.time_increment = 0.0
        msg.scan_time = 0.1
        msg.range_min = 0.02
        msg.range_max = 2.0
        
        # Invio della mappa
        msg.ranges = list(self.scan_buffer)
        self.publisher_.publish(msg)
        
def main(args=None):
    rclpy.init(args=args)
    node = TofMerger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()