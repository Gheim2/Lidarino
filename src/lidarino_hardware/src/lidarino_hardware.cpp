#include "lidarino_hardware/lidarino_hardware.hpp"
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <cmath>
#include <sys/ioctl.h>
namespace lidarino_hardware
{
    uint8_t LidarinoSystemHardware::compute_checksum(const uint8_t* data, size_t len) {
        uint8_t cs = 0;
        for (size_t i = 0; i < len; i++) cs ^= data[i];
        return cs;
    }

    hardware_interface::CallbackReturn LidarinoSystemHardware::on_init(const hardware_interface::HardwareInfo & info)
    {
        if (hardware_interface::SystemInterface::on_init(info) != hardware_interface::CallbackReturn::SUCCESS) return hardware_interface::CallbackReturn::ERROR;
        // Legge il nome della porta dall'URDF (es. /dev/ttyUSB0)
        port_name_ = info_.hardware_parameters["serial_port"];
        battery_node_ = std::make_shared<rclcpp::Node>("lidarino_hardware");
        battery_voltage_pub_ = battery_node_->create_publisher<std_msgs::msg::Float32>(
            "battery_voltage", rclcpp::QoS(10));
        battery_status_pub_ = battery_node_->create_publisher<sensor_msgs::msg::BatteryState>(
            "battery_status", rclcpp::QoS(10));
        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::CallbackReturn LidarinoSystemHardware::on_configure(const rclcpp_lifecycle::State & /*previous_state*/)
    {
        RCLCPP_INFO(rclcpp::get_logger("LidarinoHardware"), "Configurazione Lidarino hardware completata.");
        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::CallbackReturn LidarinoSystemHardware::on_activate(
    const rclcpp_lifecycle::State & /*previous_state*/)
    {
        auto logger = rclcpp::get_logger("LidarinoHardware");

        serial_fd_ = open(port_name_.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (serial_fd_ < 0) {
            RCLCPP_ERROR(logger, "Errore apertura porta seriale: %s", port_name_.c_str());
            return hardware_interface::CallbackReturn::ERROR;
        }

        struct termios tty;
        if (tcgetattr(serial_fd_, &tty) != 0) {
            RCLCPP_ERROR(logger, "tcgetattr fallita");
            close(serial_fd_);
            serial_fd_ = -1;
            return hardware_interface::CallbackReturn::ERROR;
        }

        cfmakeraw(&tty);
        cfsetospeed(&tty, B115200);
        cfsetispeed(&tty, B115200);
        tty.c_cflag |= (CLOCAL | CREAD);
        tty.c_cflag &= ~(CSTOPB | CRTSCTS | HUPCL);
        tty.c_cc[VMIN]  = 0;
        tty.c_cc[VTIME] = 0;

        if (tcsetattr(serial_fd_, TCSANOW, &tty) != 0) {
            RCLCPP_ERROR(logger, "tcsetattr fallita");
            close(serial_fd_);
            serial_fd_ = -1;
            return hardware_interface::CallbackReturn::ERROR;
        }

        // Svuota per ultimo: dopo il toggle di DTR/RTS l'ESP32 può aver già
        // mandato byte sporchi o un reset può essere in corso
        tcflush(serial_fd_, TCIOFLUSH);
        rx_buffer_.clear();

        RCLCPP_INFO(logger, "Hardware Lidarino attivato con successo.");
        return hardware_interface::CallbackReturn::SUCCESS;
    }

    hardware_interface::CallbackReturn LidarinoSystemHardware::on_deactivate(const rclcpp_lifecycle::State & /*previous_state*/)
    {
        if (serial_fd_ >= 0) close(serial_fd_);
        return hardware_interface::CallbackReturn::SUCCESS;
    }

    // Collega le variabili C++ ai topic di ros2_control
    std::vector<hardware_interface::StateInterface> LidarinoSystemHardware::export_state_interfaces()
    {
        std::vector<hardware_interface::StateInterface> state_interfaces;
        // Ruota Sinistra
        state_interfaces.emplace_back(hardware_interface::StateInterface(info_.joints[0].name, hardware_interface::HW_IF_POSITION, &hw_pos_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface(info_.joints[0].name, hardware_interface::HW_IF_VELOCITY, &hw_vel_[0]));
        // Ruota Destra
        state_interfaces.emplace_back(hardware_interface::StateInterface(info_.joints[1].name, hardware_interface::HW_IF_POSITION, &hw_pos_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface(info_.joints[1].name, hardware_interface::HW_IF_VELOCITY, &hw_vel_[1]));
        // IMU
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "accel_x", &hw_imu_accel_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "accel_y", &hw_imu_accel_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "accel_z", &hw_imu_accel_[2]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "gyro_x", &hw_imu_gyro_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "gyro_y", &hw_imu_gyro_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "gyro_z", &hw_imu_gyro_[2]));
        // Batteria
        state_interfaces.emplace_back(hardware_interface::StateInterface("battery_sensor", "voltage", &hw_battery_voltage_));
        return state_interfaces;
    }

    std::vector<hardware_interface::CommandInterface> LidarinoSystemHardware::export_command_interfaces()
    {
        std::vector<hardware_interface::CommandInterface> command_interfaces;
        command_interfaces.emplace_back(hardware_interface::CommandInterface(info_.joints[0].name, hardware_interface::HW_IF_VELOCITY, &hw_cmds_[0]));
        command_interfaces.emplace_back(hardware_interface::CommandInterface(info_.joints[1].name, hardware_interface::HW_IF_VELOCITY, &hw_cmds_[1]));
        return command_interfaces;
    }

    // ---------------------------------------------------------
    // READ: Orange Pi <- ESP32 (Telemetria)
    // ---------------------------------------------------------
    hardware_interface::return_type LidarinoSystemHardware::read(const rclcpp::Time & /*time*/, const rclcpp::Duration & period)
    {
        uint8_t buf[256];
        int n = ::read(serial_fd_, buf, sizeof(buf));
        RCLCPP_INFO_THROTTLE(
            rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
            "Serial read: %d bytes, parser buffer: %zu bytes", n, rx_buffer_.size());
        if (n > 0) {
            rx_buffer_.insert(rx_buffer_.end(), buf, buf + n);
        }
        // Processa tutti i pacchetti completi nel buffer
        while (rx_buffer_.size() >= TELEMETRY_SIZE) {
            if (rx_buffer_[0] == PROTO_SYNC_0 && rx_buffer_[1] == PROTO_SYNC_1 && rx_buffer_[TELEMETRY_SIZE - 1] == 0x0D) {
                // uint8_t calculated_payload_cs = compute_checksum(
                    // rx_buffer_.data() + 2, TELEMETRY_SIZE - 4);
                // uint8_t calculated_frame_cs = compute_checksum(
                    // rx_buffer_.data(), TELEMETRY_SIZE - 2);
                const uint8_t calculated_cs = compute_checksum(rx_buffer_.data(), TELEMETRY_SIZE - 2);

                if (calculated_cs == rx_buffer_[TELEMETRY_SIZE - 2]) {
                // if (calculated_payload_cs == rx_buffer_[TELEMETRY_SIZE - 2] ||
                    // calculated_frame_cs == rx_buffer_[TELEMETRY_SIZE - 2]) {
                    // Pacchetto valido!
                    TelemetryPacket* tp = reinterpret_cast<TelemetryPacket*>(rx_buffer_.data());
                    // Calcolo: da TICK a RADIANTI
                    double new_pos_l = ((double)tp->pos_left / AS5600_TICKS_PER_REV) * 2.0 * M_PI;
                    double new_pos_r = ((double)tp->pos_right / AS5600_TICKS_PER_REV) * 2.0 * M_PI;
                    // Calcolo velocità derivata per ros2_control
                    hw_vel_[0] = (new_pos_l - hw_pos_[0]) / period.seconds();
                    hw_vel_[1] = (new_pos_r - hw_pos_[1]) / period.seconds();
                    hw_pos_[0] = new_pos_l;
                    hw_pos_[1] = new_pos_r;
                    hw_imu_accel_[0] = static_cast<double>(tp->accel_x) /1000.0;
                    hw_imu_accel_[1] = static_cast<double>(tp->accel_y) /1000.0;
                    hw_imu_accel_[2] = static_cast<double>(tp->accel_z) /1000.0;
                    hw_imu_gyro_[0] = static_cast<double>(tp->gyro_x) /1000.0;
                    hw_imu_gyro_[1] = static_cast<double>(tp->gyro_y) /1000.0;
                    hw_imu_gyro_[2] = static_cast<double>(tp->gyro_z) /1000.0;
                    hw_battery_voltage_ = tp->battery_mv / 1000.0; // Converti mV in V
                    std_msgs::msg::Float32 voltage_msg;
                    voltage_msg.data = static_cast<float>(hw_battery_voltage_);
                    battery_voltage_pub_->publish(voltage_msg);
                    sensor_msgs::msg::BatteryState battery_msg;
                    battery_msg.header.stamp = battery_node_->now();
                    battery_msg.voltage = voltage_msg.data;
                    battery_msg.percentage = static_cast<float>(std::clamp(
                        (hw_battery_voltage_ - 9.0) / (12.6 - 9.0), 0.0, 1.0));
                    battery_msg.power_supply_status =
                        sensor_msgs::msg::BatteryState::POWER_SUPPLY_STATUS_DISCHARGING;
                    battery_msg.power_supply_technology =
                        sensor_msgs::msg::BatteryState::POWER_SUPPLY_TECHNOLOGY_LIPO;
                    battery_status_pub_->publish(battery_msg);
                    // Rimuovi il pacchetto processato
                    rx_buffer_.erase(rx_buffer_.begin(), rx_buffer_.begin() + TELEMETRY_SIZE);
                    continue;
                RCLCPP_WARN_THROTTLE(
                    rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
                    "Telemetry checksum mismatch: calculated 0x%02x, received 0x%02x",
                    calculated_cs, rx_buffer_[TELEMETRY_SIZE - 2]);
                }
            }
            // Se non è sincrono, droppa un byte per riallinearsi
            rx_buffer_.erase(rx_buffer_.begin());
        }
        return hardware_interface::return_type::OK;
    }

    // ---------------------------------------------------------
    // WRITE: Orange Pi -> ESP32 (Comandi Motore)
    // ---------------------------------------------------------
    hardware_interface::return_type LidarinoSystemHardware::write(const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
    {
        RCLCPP_INFO(rclcpp::get_logger("LidarinoHardware"), "Comandi -> Sinistra: %.2f, Destra: %.2f", hw_cmds_[0], hw_cmds_[1]);
        CommandPacket cmd;
        cmd.sync0 = PROTO_SYNC_0;
        cmd.sync1 = PROTO_SYNC_1;
        // hw_cmds_ contiene i rad/s richiesti da diff_drive_controller
        cmd.vel_left = static_cast<int16_t>(hw_cmds_[0] * 1000.0);
        cmd.vel_right = static_cast<int16_t>(hw_cmds_[1] * 1000.0);
        cmd.reserved = 0;
        cmd.checksum = compute_checksum(
        reinterpret_cast<uint8_t*>(&cmd), sizeof(CommandPacket) - 2);  // sync inclusi, come il firmware
        cmd.terminator = 0x0D;
        ::write(serial_fd_, &cmd, sizeof(CommandPacket));
        return hardware_interface::return_type::OK;
    }
}  // namespace lidarino_hardware

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(lidarino_hardware::LidarinoSystemHardware, hardware_interface::SystemInterface)
