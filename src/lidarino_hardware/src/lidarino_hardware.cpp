#include "lidarino_hardware/lidarino_hardware.hpp"
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cerrno>
#include <cstring>
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
        // Associazione ruote per nome (dall'URDF), non per ordine di dichiarazione dei joint:
        // indice 0 = sinistra, 1 = destra, come pos_left/vel_left del protocollo seriale
        left_joint_ = info_.hardware_parameters["left_wheel_joint"];
        right_joint_ = info_.hardware_parameters["right_wheel_joint"];
        for (const auto & name : {left_joint_, right_joint_}) {
            const bool found = std::any_of(info_.joints.begin(), info_.joints.end(),
                [&name](const hardware_interface::ComponentInfo & j) { return j.name == name; });
            if (name.empty() || !found) {
                RCLCPP_ERROR(rclcpp::get_logger("LidarinoHardware"),
                    "Joint ruota '%s' non trovato: controlla left_wheel_joint/right_wheel_joint nell'URDF", name.c_str());
                return hardware_interface::CallbackReturn::ERROR;
            }
        }
        battery_node_ = std::make_shared<rclcpp::Node>("lidarino_hardware");
        battery_voltage_pub_ = battery_node_->create_publisher<std_msgs::msg::Float32>(
            "battery_voltage", rclcpp::QoS(10));
        battery_status_pub_ = battery_node_->create_publisher<sensor_msgs::msg::BatteryState>(
            "battery_status", rclcpp::QoS(10));
        // read() gira nel loop realtime di ros2_control: un publish() diretto può bloccarsi
        // (rmw_zenoh, publisher reliable con subscriber lento). I RealtimePublisher pubblicano da
        // un loro thread e try_publish() non blocca mai.
        battery_voltage_rt_pub_ = std::make_unique<realtime_tools::RealtimePublisher<std_msgs::msg::Float32>>(battery_voltage_pub_);
        battery_status_rt_pub_ = std::make_unique<realtime_tools::RealtimePublisher<sensor_msgs::msg::BatteryState>>(battery_status_pub_);
        return hardware_interface::CallbackReturn::SUCCESS;
    }
    hardware_interface::CallbackReturn LidarinoSystemHardware::on_configure(const rclcpp_lifecycle::State & /*previous_state*/)
    {
        RCLCPP_INFO(rclcpp::get_logger("LidarinoHardware"), "Configurazione Lidarino hardware completata.");
        return hardware_interface::CallbackReturn::SUCCESS;
    }
    // Apre e configura la porta seriale. Restituisce "" se ok, altrimenti il motivo dell'errore.
    // Usata all'attivazione e per riconnettersi se l'ESP32 si resetta (la porta USB sparisce e ricompare).
    std::string LidarinoSystemHardware::open_serial()
    {
        serial_fd_ = open(port_name_.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
        if (serial_fd_ < 0) {
            return "open(" + port_name_ + "): " + std::strerror(errno);
        }
        // Configurazione Seriale POSIX (115200 8N1, completamente raw)
        struct termios tty;
        if (tcgetattr(serial_fd_, &tty) != 0) {
            const std::string err = std::string("tcgetattr: ") + std::strerror(errno);
            close_serial();
            return err;
        }
        // cfmakeraw disattiva anche ICRNL/INLCR/IGNCR/ISTRIP: senza, il kernel
        // trasforma ogni 0x0D (terminatore dei pacchetti) in 0x0A
        cfmakeraw(&tty);
        cfsetospeed(&tty, B115200);
        cfsetispeed(&tty, B115200);
        tty.c_cflag |= (CLOCAL | CREAD);    // Ignora linee modem, abilita ricezione
        tty.c_cflag &= ~CSTOPB;             // 1 bit di stop
        tty.c_cflag &= ~CRTSCTS;            // No controllo flusso hardware
        tty.c_iflag &= ~(IXOFF | IXANY);    // cfmakeraw non li azzera
        if (tcsetattr(serial_fd_, TCSANOW, &tty) != 0) {
            const std::string err = std::string("tcsetattr: ") + std::strerror(errno);
            close_serial();
            return err;
        }
        tcflush(serial_fd_, TCIFLUSH);      // Scarta eventuali byte vecchi (es. log di boot dell'ESP32)
        rx_buffer_.clear();
        resync_position_ = true;            // dopo un reset dell'ESP32 i contatori encoder ripartono da 0
        return "";
    }
    void LidarinoSystemHardware::close_serial()
    {
        if (serial_fd_ >= 0) close(serial_fd_);
        serial_fd_ = -1;
        hw_vel_[0] = 0.0;
        hw_vel_[1] = 0.0;
    }
    // Tentativo di riconnessione al massimo una volta al secondo
    void LidarinoSystemHardware::try_reconnect()
    {
        const auto now = std::chrono::steady_clock::now();
        if (now - last_reconnect_attempt_ < std::chrono::seconds(1)) return;
        last_reconnect_attempt_ = now;
        const std::string err = open_serial();
        if (err.empty()) {
            RCLCPP_WARN(rclcpp::get_logger("LidarinoHardware"), "Porta seriale %s riaperta, ESP32 riconnesso.", port_name_.c_str());
        } else {
            RCLCPP_WARN_THROTTLE(
                rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 5000,
                "ESP32 disconnesso, riprovo ogni secondo (%s)", err.c_str());
        }
    }
    hardware_interface::CallbackReturn LidarinoSystemHardware::on_activate(const rclcpp_lifecycle::State & /*previous_state*/)
    {
        const std::string err = open_serial();
        if (!err.empty()) {
            RCLCPP_ERROR(rclcpp::get_logger("LidarinoHardware"), "Errore apertura porta seriale: %s", err.c_str());
            return hardware_interface::CallbackReturn::ERROR;
        }
        RCLCPP_INFO(rclcpp::get_logger("LidarinoHardware"), "Hardware Lidarino attivato con successo.");
        return hardware_interface::CallbackReturn::SUCCESS;
    }
    hardware_interface::CallbackReturn LidarinoSystemHardware::on_deactivate(const rclcpp_lifecycle::State & /*previous_state*/)
    {
        // Ferma le ruote subito invece di aspettare il timeout comandi dell'ESP32
        if (serial_fd_ >= 0) {
            hw_cmds_[0] = 0.0;
            hw_cmds_[1] = 0.0;
            send_command();
        }
        close_serial();
        return hardware_interface::CallbackReturn::SUCCESS;
    }
    // Collega le variabili C++ ai topic di ros2_control
    std::vector<hardware_interface::StateInterface> LidarinoSystemHardware::export_state_interfaces()
    {
        std::vector<hardware_interface::StateInterface> state_interfaces;
        // Ruota Sinistra
        state_interfaces.emplace_back(hardware_interface::StateInterface(left_joint_, hardware_interface::HW_IF_POSITION, &hw_pos_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface(left_joint_, hardware_interface::HW_IF_VELOCITY, &hw_vel_[0]));
        // Ruota Destra
        state_interfaces.emplace_back(hardware_interface::StateInterface(right_joint_, hardware_interface::HW_IF_POSITION, &hw_pos_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface(right_joint_, hardware_interface::HW_IF_VELOCITY, &hw_vel_[1]));
        // IMU
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "orientation.x", &hw_imu_orientation_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "orientation.y", &hw_imu_orientation_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "orientation.z", &hw_imu_orientation_[2]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "orientation.w", &hw_imu_orientation_[3]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "linear_acceleration.x", &hw_imu_accel_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "linear_acceleration.y", &hw_imu_accel_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "linear_acceleration.z", &hw_imu_accel_[2]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "angular_velocity.x", &hw_imu_gyro_[0]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "angular_velocity.y", &hw_imu_gyro_[1]));
        state_interfaces.emplace_back(hardware_interface::StateInterface("imu_sensor", "angular_velocity.z", &hw_imu_gyro_[2]));
        // Batteria
        state_interfaces.emplace_back(hardware_interface::StateInterface("battery_sensor", "voltage", &hw_battery_voltage_));
        return state_interfaces;
    }
    std::vector<hardware_interface::CommandInterface> LidarinoSystemHardware::export_command_interfaces()
    {
        std::vector<hardware_interface::CommandInterface> command_interfaces;
        command_interfaces.emplace_back(hardware_interface::CommandInterface(left_joint_, hardware_interface::HW_IF_VELOCITY, &hw_cmds_[0]));
        command_interfaces.emplace_back(hardware_interface::CommandInterface(right_joint_, hardware_interface::HW_IF_VELOCITY, &hw_cmds_[1]));
        return command_interfaces;
    }
    // ---------------------------------------------------------
    // READ: Orange Pi <- ESP32 (Telemetria)
    // ---------------------------------------------------------
    hardware_interface::return_type LidarinoSystemHardware::read(const rclcpp::Time & /*time*/, const rclcpp::Duration & period)
    {
        if (serial_fd_ < 0) {
            try_reconnect();
            return hardware_interface::return_type::OK;
        }
        uint8_t buf[256];
        const ssize_t n = ::read(serial_fd_, buf, sizeof(buf));
        RCLCPP_DEBUG_THROTTLE(
            rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
            "Serial read: %zd bytes, parser buffer: %zu bytes", n, rx_buffer_.size());
        if (n > 0) {
            rx_buffer_.insert(rx_buffer_.end(), buf, buf + n);
        } else if (n == 0 || (errno != EAGAIN && errno != EWOULDBLOCK)) {
            // n == 0 (hangup) o errore vero (es. EIO): la porta USB è sparita, tipicamente per un reset dell'ESP32
            RCLCPP_ERROR(rclcpp::get_logger("LidarinoHardware"), "Porta seriale persa (%s), riconnessione in corso",
                n == 0 ? "hangup" : std::strerror(errno));
            close_serial();
            return hardware_interface::return_type::OK;
        }
        // Processa tutti i pacchetti completi nel buffer
        while (rx_buffer_.size() >= TELEMETRY_SIZE) {
            if (rx_buffer_[0] == PROTO_SYNC_0 && rx_buffer_[1] == PROTO_SYNC_1 && rx_buffer_[TELEMETRY_SIZE - 1] == 0x0D) {
                // XOR di tutti i byte prima del checksum, sync inclusi (come serial_protocol.h)
                uint8_t calculated_cs = compute_checksum(rx_buffer_.data(), TELEMETRY_SIZE - 2);
                if (calculated_cs == rx_buffer_[TELEMETRY_SIZE - 2]) {
                    // Pacchetto valido!
                    TelemetryPacket* tp = reinterpret_cast<TelemetryPacket*>(rx_buffer_.data());
                    if (!(tp->status_flags & STATUS_BIT_IMU_OK)) {
                        RCLCPP_WARN_THROTTLE(
                            rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
                            "ESP32 riporta IMU non funzionante: dati IMU non aggiornati");
                    }
                    // Calcolo: da TICK a RADIANTI
                    double raw_pos_l = ((double)tp->pos_left / AS5600_TICKS_PER_REV) * 2.0 * M_PI;
                    double raw_pos_r = ((double)tp->pos_right / AS5600_TICKS_PER_REV) * 2.0 * M_PI;
                    if (resync_position_) {
                        // Primo pacchetto dopo apertura/riconnessione: la posizione continua da dove era,
                        // così un reset dell'ESP32 (contatori a 0) non crea salti nell'odometria
                        pos_offset_[0] = hw_pos_[0] - raw_pos_l;
                        pos_offset_[1] = hw_pos_[1] - raw_pos_r;
                        resync_position_ = false;
                    }
                    double new_pos_l = raw_pos_l + pos_offset_[0];
                    double new_pos_r = raw_pos_r + pos_offset_[1];
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
                    // 1 Hz: il firmware misura la batteria una volta al secondo
                    const auto now = std::chrono::steady_clock::now();
                    if (now - last_battery_publish_ >= std::chrono::seconds(1)) {
                        last_battery_publish_ = now;
                        std_msgs::msg::Float32 voltage_msg;
                        voltage_msg.data = static_cast<float>(hw_battery_voltage_);
                        battery_voltage_rt_pub_->try_publish(voltage_msg);
                        sensor_msgs::msg::BatteryState battery_msg;
                        battery_msg.header.stamp = battery_node_->now();
                        battery_msg.voltage = voltage_msg.data;
                        battery_msg.percentage = static_cast<float>(std::clamp(
                            (hw_battery_voltage_ - 9.0) / (12.6 - 9.0), 0.0, 1.0));
                        battery_msg.power_supply_status =
                            sensor_msgs::msg::BatteryState::POWER_SUPPLY_STATUS_DISCHARGING;
                        battery_msg.power_supply_technology =
                            sensor_msgs::msg::BatteryState::POWER_SUPPLY_TECHNOLOGY_LIPO;
                        battery_status_rt_pub_->try_publish(battery_msg);
                    }
                    // Rimuovi il pacchetto processato
                    rx_buffer_.erase(rx_buffer_.begin(), rx_buffer_.begin() + TELEMETRY_SIZE);
                    continue;
                }
                RCLCPP_WARN_THROTTLE(
                    rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
                    "Telemetry checksum mismatch: calculated 0x%02x, received 0x%02x",
                    calculated_cs, rx_buffer_[TELEMETRY_SIZE - 2]);
            }
            // Se non è sincrono, droppa un byte per riallinearsi.
            // I byte scartati che formano testo (es. "[BOOT] reset_reason=..." del firmware) vengono riportati nel log.
            const char c = static_cast<char>(rx_buffer_.front());
            if (c == '\n') {
                if (esp_text_line_.rfind("[BOOT]", 0) == 0) {
                    RCLCPP_WARN(rclcpp::get_logger("LidarinoHardware"), "ESP32: %s", esp_text_line_.c_str());
                }
                esp_text_line_.clear();
            } else if (c >= 0x20 && c <= 0x7E && esp_text_line_.size() < 120) {
                esp_text_line_.push_back(c);
            } else {
                esp_text_line_.clear();  // byte binario: non è una riga di testo
            }
            rx_buffer_.erase(rx_buffer_.begin());
        }
        return hardware_interface::return_type::OK;
    }
    // ---------------------------------------------------------
    // WRITE: Orange Pi -> ESP32 (Comandi Motore)
    // ---------------------------------------------------------
    hardware_interface::return_type LidarinoSystemHardware::write(const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
    {
        // Durante la riconnessione non si invia nulla: l'ESP32 azzera i target da solo dopo il timeout comandi
        if (serial_fd_ < 0) return hardware_interface::return_type::OK;
        RCLCPP_DEBUG_THROTTLE(
            rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 1000,
            "Comandi -> Sinistra: %.2f, Destra: %.2f", hw_cmds_[0], hw_cmds_[1]);
        send_command();
        // Mai ERROR: ros2_control disattiverebbe hardware e controller per un singolo errore
        // transitorio, senza più recuperare. Gli errori gravi chiudono la porta e read() riconnette.
        return hardware_interface::return_type::OK;
    }
    void LidarinoSystemHardware::send_command()
    {
        CommandPacket cmd;
        cmd.sync0 = PROTO_SYNC_0;
        cmd.sync1 = PROTO_SYNC_1;
        // hw_cmds_ contiene i rad/s richiesti da diff_drive_controller
        // Saturazione al range di int16: un cast fuori range è undefined behavior
        // e in pratica fa wrap, invertendo il verso della ruota
        cmd.vel_left = static_cast<int16_t>(std::clamp(hw_cmds_[0] * 1000.0, -32768.0, 32767.0));
        cmd.vel_right = static_cast<int16_t>(std::clamp(hw_cmds_[1] * 1000.0, -32768.0, 32767.0));
        cmd.reserved = 0;
        // The firmware XORs every byte before checksum, including both sync
        // bytes. Keep this identical to serial_protocol.h on the ESP32.
        cmd.checksum = compute_checksum(
            reinterpret_cast<uint8_t*>(&cmd), sizeof(CommandPacket) - 2);
        cmd.terminator = 0x0D;
        const ssize_t bytes_written = ::write(serial_fd_, &cmd, sizeof(CommandPacket));
        if (bytes_written == static_cast<ssize_t>(sizeof(CommandPacket))) return;
        if (bytes_written >= 0) {
            // Scrittura parziale: il firmware scarta il pacchetto troncato e si risincronizza
            RCLCPP_WARN_THROTTLE(
                rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
                "Serial write parziale: %zd/%zu byte", bytes_written, sizeof(CommandPacket));
        } else if (errno == EAGAIN || errno == EWOULDBLOCK) {
            // Buffer di uscita pieno: l'ESP32 non sta leggendo (bloccato o in reset). Si salta il ciclo.
            RCLCPP_WARN_THROTTLE(
                rclcpp::get_logger("LidarinoHardware"), *battery_node_->get_clock(), 2000,
                "Serial write: buffer pieno, l'ESP32 non legge i comandi (comando saltato)");
        } else {
            RCLCPP_ERROR(rclcpp::get_logger("LidarinoHardware"), "Serial write fallita (%s), riconnessione in corso",
                std::strerror(errno));
            close_serial();
        }
    }
}  // namespace lidarino_hardware
#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(lidarino_hardware::LidarinoSystemHardware, hardware_interface::SystemInterface)
