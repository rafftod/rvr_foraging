#!/usr/bin/env python3


"""The purpose of this script is to make the robot
turn around, to test that UART can work properly for a longer
operating time when using the treads and sensors.

To stop the script, use Ctrl+Z.
"""

from datetime import datetime
import time
import rospy
import os
import sys
from typing import Dict
from driver_logger import DriverLogger


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from sphero_sdk import SpheroRvrObserver
from sphero_sdk.common.rvr_streaming_services import RvrStreamingServices


class SensingTest(DriverLogger):

    speed_params = {"left_velocity": -0.5, "right_velocity": 0.5}
    BATTERY_MEASURE_TIMEOUT = 120
    SENSOR_STREAMING_INTERVAL = 500

    def __init__(self) -> None:
        # init ROS node
        rospy.init_node("rvr_driving_test")
        # init robot API connection
        self.log("Starting RVR API...")
        self.rvr = SpheroRvrObserver()
        # sensor values
        # battery
        self.battery_percentage: float = 0
        # accelerometer
        self.accelerometer_reading: Dict[str, float] = {"X": 0, "Y": 0, "Z": 0}
        # ground color sensor
        self.ground_color: Dict[str, int] = {"R": 0, "G": 0, "B": 0}
        # gyroscope
        self.angular_velocity: Dict[str, float] = {"X": 0, "Y": 0, "Z": 0}
        # IMU
        self.imu_reading: Dict[str, float] = {"Pitch": 0, "Roll": 0, "Yaw": 0}
        # light sensor
        self.ambient_light: float = 0
        # locator
        self.location: Dict[str, float] = {"X": 0, "Y": 0}
        # quaternion
        self.quat_reading: Dict[str, float] = {"W": 0, "X": 0, "Y": 0, "Z": 0}
        # velocity
        self.velocity_reading: Dict[str, float] = {"X": 0, "Y": 0}
        self.setup_rvr()

    def setup_rvr(self) -> None:
        self.log("Waking up RVR...")
        self.rvr.wake()
        time.sleep(2)
        self.rvr.reset_yaw()
        self.enable_sensors()

    """ Robot Handlers """

    def battery_percentage_handler(self, bp: Dict[str, float]) -> None:
        self.battery_percentage = bp.get("percentage")

    def accelerometer_handler(self, data: Dict[str, float]) -> None:
        self.accelerometer_reading.update(data["Accelerometer"])

    def ground_sensor_handler(self, data) -> None:
        self.ground_color.update(data["ColorDetection"])

    def gyroscope_handler(self, data) -> None:
        self.angular_velocity.update(data["Gyroscope"])

    def imu_handler(self, data) -> None:
        self.imu_reading.update(data["IMU"])

    def light_handler(self, data) -> None:
        self.ambient_light = data["AmbientLight"]["Light"]

    def locator_handler(self, data) -> None:
        self.location.update(data["Locator"])

    def quaternion_handler(self, data) -> None:
        self.quat_reading.update(data["Quaternion"])

    def velocity_handler(self, data) -> None:
        self.velocity_reading.update(data["Velocity"])

    def enable_sensors(self) -> None:
        self.log("Enabling sensors...")
        self.rvr.enable_color_detection(is_enabled=True)
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.accelerometer,
            handler=self.accelerometer_handler,
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.color_detection,
            handler=self.ground_sensor_handler,
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.gyroscope, handler=self.gyroscope_handler
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.imu, handler=self.imu_handler
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.ambient_light, handler=self.light_handler
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.locator, handler=self.locator_handler
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.quaternion, handler=self.quaternion_handler
        )
        self.rvr.sensor_control.add_sensor_data_handler(
            service=RvrStreamingServices.velocity, handler=self.velocity_handler
        )
        self.rvr.sensor_control.start(interval=self.SENSOR_STREAMING_INTERVAL)

    def test_loop(self):
        last_measure_time = datetime.now().timestamp()
        self.rvr.get_battery_percentage(handler=self.battery_percentage_handler)
        # wait for battery response
        time.sleep(1)
        self.log(f"Current battery level : {self.battery_percentage}")
        while not rospy.is_shutdown():
            try:
                self.rvr.drive_tank_si_units(**self.speed_params)
                if (
                    datetime.now().timestamp() - last_measure_time
                    > self.BATTERY_MEASURE_TIMEOUT
                ):
                    self.rvr.get_battery_percentage(
                        handler=self.battery_percentage_handler
                    )
                    # wait for battery response
                    time.sleep(1)
                    self.log(f"Current battery level : {self.battery_percentage}")
                    last_measure_time = datetime.now().timestamp()
                else:
                    time.sleep(1)
                self.log(self.ground_color.__repr__())
            except KeyboardInterrupt:
                self.log("Keyboard interrupted.")
                # rospy.signal_shutdown()
                self.rvr.sensor_control.clear()
                time.sleep(0.5)
                self.rvr.close()
                exit()


if __name__ == "__main__":
    driving_test = SensingTest()
    driving_test.test_loop()
