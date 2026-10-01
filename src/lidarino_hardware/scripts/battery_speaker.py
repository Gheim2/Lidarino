#!/usr/bin/env python3
import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class BatterySpeaker(Node):
    def __init__(self):
        super().__init__('battery_speaker')
        self.declare_parameter('alsa_device', 'plughw:1,0')
        self.declare_parameter('period_s', 20.0)
        self.declare_parameter('v_empty', 9.0)
        self.declare_parameter('v_full', 12.6)

        self.device = self.get_parameter('alsa_device').value
        self.v_empty = self.get_parameter('v_empty').value
        self.v_full = self.get_parameter('v_full').value
        period = self.get_parameter('period_s').value

        self.voltage = None
        self.player = None  # processo aplay in corso

        self.create_subscription(Float32, 'battery_voltage', self.on_voltage, 10)
        self.create_timer(period, self.speak)

    def on_voltage(self, msg):
        self.voltage = msg.data

    def speak(self):
        if self.voltage is None:
            self.get_logger().warn('Nessun valore di batteria ricevuto, non parlo')
            return
        # Se sta ancora parlando, salta questo giro
        if self.player is not None and self.player.poll() is None:
            return

        v = self.voltage
        pct = int(max(0.0, min(1.0, (v - self.v_empty) / (self.v_full - self.v_empty))) * 100)
        text = f'Batteria al {pct} percento, {v:.1f} volt'.replace('.', ',')
        self.get_logger().info(f'Parlo: {text}')

        tts = subprocess.Popen(['espeak-ng', '-v', 'it', '--stdout', text],
                               stdout=subprocess.PIPE)
        self.player = subprocess.Popen(['aplay', '-q', '-D', self.device],
                                       stdin=tts.stdout)
        tts.stdout.close()


def main():
    rclpy.init()
    rclpy.spin(BatterySpeaker())
    rclpy.shutdown()


if __name__ == '__main__':
    main()