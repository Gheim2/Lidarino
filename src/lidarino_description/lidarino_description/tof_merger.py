#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import math

class TofMerger(Node):
    def __init__(self):
        super().__init__('tof_merger')
        
        # Il publisher del LiDAR fuso a 360 gradi
        self.publisher_ = self.create_publisher(LaserScan, '/scan', 10)
        
        # Sottoscrizioni ai 6 ToF
        self.create_subscription(LaserScan, '/scan_tof_1', self.tof1_cb, 10)
        self.create_subscription(LaserScan, '/scan_tof_2', self.tof2_cb, 10)
        self.create_subscription(LaserScan, '/scan_tof_3', self.tof3_cb, 10)
        self.create_subscription(LaserScan, '/scan_tof_4', self.tof4_cb, 10)
        
        # Dizionario per memorizzare le ultime letture
        self.ranges = {
            'tof_1': float('inf'), 'tof_2': float('inf'), 
            'tof_3': float('inf'), 'tof_4': float('inf')
        }
        
        # Timer a 10Hz per pubblicare il pacchetto fuso
        self.timer = self.create_timer(0.1, self.publish_merged_scan)

    def get_min_distance(self, msg):
        """Estrae la distanza minima dal cono dei ToF, ignorando i valori fuori range"""
        valid_ranges = [r for r in msg.ranges if 0.05 < r < 2.0]
        if valid_ranges:
            return min(valid_ranges)
        return float('inf')
    
    # Callback dei sensori: aggiornano l'ultima distanza letta
    def tof1_cb(self, msg): self.ranges['tof_1'] = self.get_min_distance(msg)
    def tof2_cb(self, msg): self.ranges['tof_2'] = self.get_min_distance(msg)
    def tof3_cb(self, msg): self.ranges['tof_3'] = self.get_min_distance(msg)
    def tof4_cb(self, msg): self.ranges['tof_4'] = self.get_min_distance(msg)

    def publish_merged_scan(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        # Agganciamo il finto sensore al centro del componente Lidar
        msg.header.frame_id = 'lidar' 
        
        # Creiamo un LiDAR a 360 gradi, risoluzione 1 grado
        msg.angle_increment = math.pi / 180.0 # 1 grado in radianti
        msg.angle_min = -math.pi
        msg.angle_max = math.pi - msg.angle_increment
        msg.time_increment = 0.0
        msg.scan_time = 0.1
        msg.range_min = 0.02
        msg.range_max = 2.0
        
        # Inizializza 360 raggi all'infinito
        merged_ranges = [float('inf')] * 360
        
        def set_range(angle_deg, distance):
            # Normalizza l'angolo sull'indice dell'array
            idx = int(angle_deg + 180) % 360
            merged_ranges[idx] = distance

        set_range(0, self.ranges['tof_1'])
        set_range(90, self.ranges['tof_2'])
        set_range(180, self.ranges['tof_3'])
        set_range(-90, self.ranges['tof_4'])
        
        msg.ranges = merged_ranges
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = TofMerger()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()