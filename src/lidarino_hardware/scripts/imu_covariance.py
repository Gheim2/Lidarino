#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from rclpy.qos import qos_profile_sensor_data
import sys

class ImuCovarianceCalculator(Node):
    def __init__(self):
        super().__init__('imu_covariance_calculator')
        
        # qos_profile_sensor_data perché i driver hardware 
        # pubblicano in modalità "Best Effort"
        self.subscription = self.create_subscription(
            Imu,
            '/imu/data_raw',
            self.imu_callback,
            qos_profile_sensor_data)
            
        self.get_logger().info("In attesa dei dati IMU...")
        self.get_logger().warn("ATTENZIONE: MANTENI IL ROBOT COMPLETAMENTE FERMO E A MOTORI SPENTI!")
        
        self.target_samples = 1000
        self.current_samples = 0
        
        # Liste per memorizzare i dati storici
        self.ax, self.ay, self.az = [], [], []
        self.gx, self.gy, self.gz = [], [], []

    def imu_callback(self, msg):
        if self.current_samples >= self.target_samples:
            return

        # Salvataggio dati accelerometro
        self.ax.append(msg.linear_acceleration.x)
        self.ay.append(msg.linear_acceleration.y)
        self.az.append(msg.linear_acceleration.z)
        
        # Salvataggio dati giroscopio
        self.gx.append(msg.angular_velocity.x)
        self.gy.append(msg.angular_velocity.y)
        self.gz.append(msg.angular_velocity.z)
        
        self.current_samples += 1
        
        if self.current_samples % 200 == 0:
            self.get_logger().info(f"Raccolti {self.current_samples}/{self.target_samples} campioni...")
            
        if self.current_samples == self.target_samples:
            self.calculate_and_print()
            sys.exit(0)

    def calculate_and_print(self):
        # Funzione helper per calcolare la varianza (σ^2)
        def calc_variance(data_list):
            mean = sum(data_list) / len(data_list)
            return sum((x - mean) ** 2 for x in data_list) / len(data_list)

        var_ax = calc_variance(self.ax)
        var_ay = calc_variance(self.ay)
        var_az = calc_variance(self.az)
        
        var_gx = calc_variance(self.gx)
        var_gy = calc_variance(self.gy)
        var_gz = calc_variance(self.gz)

        print("\n" + "="*60)
        print(" CALCOLO COMPLETATO: COPIA QUESTO NEL TUO NODO C++")
        print("="*60)
        print("// Matrice covarianza Accelerazione Lineare (Diagonale)")
        print(f"msg.linear_acceleration_covariance[0] = {var_ax:.8f}; // X")
        print(f"msg.linear_acceleration_covariance[4] = {var_ay:.8f}; // Y")
        print(f"msg.linear_acceleration_covariance[8] = {var_az:.8f}; // Z")
        print("-" * 60)
        print("// Matrice covarianza Velocità Angolare (Diagonale)")
        print(f"msg.angular_velocity_covariance[0] = {var_gx:.8f}; // Roll")
        print(f"msg.angular_velocity_covariance[4] = {var_gy:.8f}; // Pitch")
        print(f"msg.angular_velocity_covariance[8] = {var_gz:.8f}; // Yaw")
        print("="*60 + "\n")

def main(args=None):
    rclpy.init(args=args)
    try:
        node = ImuCovarianceCalculator()
        rclpy.spin(node)
    except SystemExit:
        pass # Uscita pulita causata dal sys.exit(0)
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()