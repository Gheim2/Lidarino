#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from rclpy.qos import qos_profile_sensor_data
import sys

class ImuCovarianceCalculator(Node):
    def __init__(self):
        super().__init__('imu_covariance_calculator')
        
        # imu_broadcaster pubblica "Reliable": una sottoscrizione "Best Effort"
        # (qos_profile_sensor_data) è compatibile e non rallenta il publisher
        self.subscription = self.create_subscription(
            Imu,
            '/imu_broadcaster/imu',
            self.imu_callback,
            qos_profile_sensor_data)
            
        self.get_logger().info("In attesa dei dati IMU...")
        self.get_logger().warn("ATTENZIONE: MANTENI IL ROBOT COMPLETAMENTE FERMO E A MOTORI SPENTI!")
        
        # 1000 campioni distinti: l'ESP32 manda dati a 50 Hz, quindi circa 20 s
        self.target_samples = 1000
        self.current_samples = 0
        self.last_values = None

        # Liste per memorizzare i dati storici
        self.ax, self.ay, self.az = [], [], []
        self.gx, self.gy, self.gz = [], [], []

    def imu_callback(self, msg):
        if self.current_samples >= self.target_samples:
            return

        # imu_broadcaster pubblica a 100 Hz ma i dati arrivano a 50 Hz: ogni campione
        # compare due volte. I duplicati non vanno contati (falserebbero la statistica).
        values = (msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z,
                  msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z)
        if values == self.last_values:
            return
        self.last_values = values

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
        def calc_mean(data_list):
            return sum(data_list) / len(data_list)

        # Funzione helper per calcolare la varianza (σ^2)
        def calc_variance(data_list):
            mean = calc_mean(data_list)
            return sum((x - mean) ** 2 for x in data_list) / len(data_list)

        accel = (self.ax, self.ay, self.az)
        gyro = (self.gx, self.gy, self.gz)
        var_accel = [calc_variance(d) for d in accel]
        var_gyro = [calc_variance(d) for d in gyro]

        # Covarianze diagonali (matrice 3x3 riga per riga, come in sensor_msgs/Imu)
        def diagonal(v):
            return [v[0], 0.0, 0.0, 0.0, v[1], 0.0, 0.0, 0.0, v[2]]

        def fmt(values):
            return "[" + ", ".join(f"{x:.3e}" if x else "0.0" for x in values) + "]"

        print("\n" + "="*60)
        print(" CALCOLO COMPLETATO")
        print("="*60)
        print("Medie (robot fermo e in piano: accel ~ 0, 0, +9.81; gyro ~ 0, 0, 0):")
        print("  accel = " + ", ".join(f"{calc_mean(d):+.4f}" for d in accel) + " m/s^2")
        print("  gyro  = " + ", ".join(f"{calc_mean(d):+.5f}" for d in gyro) + " rad/s")
        print("-" * 60)
        print("Da copiare in config/controllers_real.yaml, sotto imu_broadcaster/ros__parameters:")
        print(f"    static_covariance_orientation: [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # orientamento non disponibile (REP 145)")
        print(f"    static_covariance_angular_velocity: {fmt(diagonal(var_gyro))}")
        print(f"    static_covariance_linear_acceleration: {fmt(diagonal(var_accel))}")
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