import time
from robot.irl.config import buildIRLSystemInterface, IRLSystemInterface, buildIRLConfig
from robot.irl.motors import Servo, DCMotor
from robot.global_config import GlobalConfig, buildGlobalConfig


def main() -> None:
    global_config = buildGlobalConfig()
    irl_config = buildIRLConfig()
    system: IRLSystemInterface = buildIRLSystemInterface(irl_config, global_config)

    arduino = system["arduino"]
    distribution_modules = system["distribution_modules"]
    main_conveyor_motor = system["main_conveyor_dc_motor"]
    feeder_conveyor_motor = system["feeder_conveyor_dc_motor"]
    vibration_hopper_motor = system["vibration_hopper_dc_motor"]

    debug_level = global_config["debug_level"]
    if debug_level > 0:
        print(f"Running with debug level: {debug_level}")

    try:
        print("Testing DC motors at speed 100...")
        #main_conveyor_motor.setSpeed(100)
        #feeder_conveyor_motor.setSpeed(100)
        vibration_hopper_motor.setSpeed(255)

        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        print("Stopping motors...")
        main_conveyor_motor.setSpeed(0)
        feeder_conveyor_motor.setSpeed(0)
        vibration_hopper_motor.setSpeed(0)


if __name__ == "__main__":
    main()
