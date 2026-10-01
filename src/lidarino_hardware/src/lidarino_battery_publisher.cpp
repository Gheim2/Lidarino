#include <algorithm>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/battery_state.hpp"
#include "std_msgs/msg/float32.hpp"

class LidarinoBatteryPublisher : public rclcpp::Node
{
public:
    LidarinoBatteryPublisher()
    : Node("lidarino_battery_publisher")
    {
        battery_pub_ = create_publisher<sensor_msgs::msg::BatteryState>(
            "battery_status", rclcpp::SensorDataQoS());
        voltage_sub_ = create_subscription<std_msgs::msg::Float32>(
            "battery_voltage", rclcpp::SensorDataQoS(),
            [this](const std_msgs::msg::Float32::SharedPtr message) {
                sensor_msgs::msg::BatteryState battery;
                battery.header.stamp = now();
                battery.voltage = message->data;
                battery.percentage = std::max(
                    0.0f, std::min(1.0f, (message->data - 9.0f) / (12.6f - 9.0f)));
                battery.power_supply_status =
                    sensor_msgs::msg::BatteryState::POWER_SUPPLY_STATUS_DISCHARGING;
                battery.power_supply_technology =
                    sensor_msgs::msg::BatteryState::POWER_SUPPLY_TECHNOLOGY_LIPO;
                battery_pub_->publish(battery);
            });
    }

private:
    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr voltage_sub_;
    rclcpp::Publisher<sensor_msgs::msg::BatteryState>::SharedPtr battery_pub_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<LidarinoBatteryPublisher>());
    rclcpp::shutdown();
    return 0;
}
