#pragma once

#include <chrono>
#include <vector>
#include <string>
#include "hardware_interface/system_interface.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "rclcpp/rclcpp.hpp"
#include "realtime_tools/realtime_publisher.hpp"
#include <memory>
#include "sensor_msgs/msg/battery_state.hpp"
#include "std_msgs/msg/float32.hpp"

namespace lidarino_hardware
{

// --- PROTOCOLLO SERIALE (Esattamente come su ESP32) ---
#define PROTO_SYNC_0   0xAA
#define PROTO_SYNC_1   0x55
#define AS5600_TICKS_PER_REV 4096

// Bit del campo status_flags
#define STATUS_BIT_ESTOP        (1 << 0)
#define STATUS_BIT_ENCODER_L_OK (1 << 1)
#define STATUS_BIT_ENCODER_R_OK (1 << 2)
#define STATUS_BIT_IMU_OK       (1 << 3)

#pragma pack(push, 1)
struct CommandPacket {
    uint8_t  sync0;
    uint8_t  sync1;
    int16_t  vel_left;    // rad/s * 1000
    int16_t  vel_right;   // rad/s * 1000
    uint16_t reserved;
    uint8_t  checksum;
    uint8_t  terminator;
};
struct TelemetryPacket {
    uint8_t  sync0;
    uint8_t  sync1;
    int32_t  pos_left;
    int32_t  pos_right;
    int16_t  accel_x;
    int16_t  accel_y;
    int16_t  accel_z;
    int16_t  gyro_x;
    int16_t  gyro_y;
    int16_t  gyro_z;
    uint8_t  status_flags;
    uint16_t battery_mv;
    uint8_t  checksum;
    uint8_t  terminator;
};
#pragma pack(pop)

#define TELEMETRY_SIZE sizeof(TelemetryPacket)


class LidarinoSystemHardware : public hardware_interface::SystemInterface
{
public:
    hardware_interface::CallbackReturn on_init(const hardware_interface::HardwareInfo & info) override;
    hardware_interface::CallbackReturn on_configure(const rclcpp_lifecycle::State & previous_state) override;
    hardware_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;
    hardware_interface::CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;

    std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
    std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

    hardware_interface::return_type read(const rclcpp::Time & time, const rclcpp::Duration & period) override;
    hardware_interface::return_type write(const rclcpp::Time & time, const rclcpp::Duration & period) override;

private:
    uint8_t compute_checksum(const uint8_t* data, size_t len);
    std::string open_serial();   // "" se ok, altrimenti il motivo dell'errore
    void close_serial();
    void try_reconnect();
    void send_command();         // invia hw_cmds_ all'ESP32

    std::chrono::steady_clock::time_point last_reconnect_attempt_{};
    bool resync_position_ = true;                // al primo pacchetto dopo (ri)connessione
    std::vector<double> pos_offset_ = {0.0, 0.0}; // continuità della posizione dopo un reset dell'ESP32
    std::string esp_text_line_;                   // testo ricevuto fuori dai pacchetti (report di boot)

    // File descriptor per la porta seriale (Linux POSIX)
    int serial_fd_ = -1;
    std::string port_name_;
    std::string left_joint_;   // joint ruota sinistra (pos_left/vel_left), da URDF
    std::string right_joint_;  // joint ruota destra (pos_right/vel_right), da URDF

    // Array per memorizzare i valori delle interfacce (Ruota Sinistra [0], Ruota Destra [1])
    std::vector<double> hw_cmds_ = {0.0, 0.0};
    std::vector<double> hw_pos_ = {0.0, 0.0};
    std::vector<double> hw_vel_ = {0.0, 0.0};
    
    std::vector<double> hw_imu_orientation_ = {0.0, 0.0, 0.0, 1.0}; // orientation.x, orientation.y, orientation.z, orientation.w
    std::vector<double> hw_imu_accel_ = {0.0, 0.0, 0.0}; // accel_x, accel_y, accel_z
    std::vector<double> hw_imu_gyro_ = {0.0, 0.0, 0.0};  // gyro_x, gyro_y, gyro_z
    double hw_battery_voltage_ = 0.0;

    // Buffer per il parsing seriale in ricezione
    std::vector<uint8_t> rx_buffer_;
    
    rclcpp::Node::SharedPtr battery_node_;
    rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr battery_voltage_pub_;
    rclcpp::Publisher<sensor_msgs::msg::BatteryState>::SharedPtr battery_status_pub_;
    std::unique_ptr<realtime_tools::RealtimePublisher<std_msgs::msg::Float32>> battery_voltage_rt_pub_;
    std::unique_ptr<realtime_tools::RealtimePublisher<sensor_msgs::msg::BatteryState>> battery_status_rt_pub_;
    std::chrono::steady_clock::time_point last_battery_publish_{};
};

}  // namespace lidarino_hardware
