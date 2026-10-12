#!/usr/bin/env python3
import subprocess
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class BatterySpeaker(Node):
    def __init__(self):
        super().__init__('battery_speaker')
        self.declare_parameter('alsa_device', 'plughw:1,0')
        self.declare_parameter('sample_duration_s', 3.0)
        self.declare_parameter('v_empty', 10.0)
        self.declare_parameter('v_full', 12.6)

        self.device = self.get_parameter('alsa_device').value
        self.v_empty = self.get_parameter('v_empty').value
        self.v_full = self.get_parameter('v_full').value
        self.sample_duration = float(self.get_parameter('sample_duration_s').value)

        self.voltages = []
        self.player = None  # processo aplay in corso

        self.create_subscription(Float32, 'battery_voltage', self.on_voltage, 10)

    def on_voltage(self, msg):
        self.voltages.append(msg.data)
        if len(self.voltages) > 1000:
            self.voltages.pop(0)

    def speak(self):
        if not self.voltages:
            self.get_logger().warn('Nessun valore di batteria ricevuto, non parlo')
            return
        # Se sta ancora parlando, salta questo giro
        if self.player is not None and self.player.poll() is None:
            self.voltages.clear()
            return

        # Calcolo la media grezza
        num_readings = len(self.voltages)
        raw_v = sum(self.voltages) / num_readings
        self.voltages.clear()

        v = round(raw_v, 1)
        pct = int(max(0.0, min(1.0, (v - self.v_empty) / (self.v_full - self.v_empty))) * 100)
        text = f'Batteria al {pct} percento, {v:.1f} volt'.replace('.', ',')

        self.get_logger().info(f'Parlo: {text} (Media calcolata su {num_readings} letture)')

        audio_file = '/tmp/battery_status.wav'
        subprocess.run(['pico2wave', '-l', 'it-IT', '-w', audio_file, text])

        self.player = subprocess.Popen(['aplay', '-q', '-D', self.device, audio_file])


def main():
    rclpy.init()
    node = BatterySpeaker()
    try:
        end_time = time.monotonic() + node.sample_duration

        # Process subscription callbacks for at least sample_duration seconds.
        while time.monotonic() < end_time:
            remaining = end_time - time.monotonic()

            # Use a short timeout so the loop remains responsive.
            rclpy.spin_once(
                node,
                timeout_sec=min(0.1, max(0.0, remaining))
            )

        # Speak once, after the complete sampling period.
        node.speak()

        # Optional: keep the process alive until aplay finishes.
        if node.player is not None:
            node.player.wait()

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()