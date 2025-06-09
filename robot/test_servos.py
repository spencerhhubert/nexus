import time
import os
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface


def main():
    gc = buildGlobalConfig()
    logger = gc["logger"]

    logger.info("Building IRL configuration...")
    irl_config = buildIRLConfig()

    logger.info("Connecting to hardware and setting up servos...")
    irl_system = buildIRLSystemInterface(irl_config, gc)

    # Get servo angles from global config
    conveyor_door_open_angle = gc["conveyor_door_open_angle"]
    conveyor_door_closed_angle = gc["conveyor_door_closed_angle"]
    bin_door_open_angle = gc["bin_door_open_angle"]
    bin_door_closed_angle = gc["bin_door_closed_angle"]

    logger.info(f"Conveyor door angles: closed={conveyor_door_closed_angle}°, open={conveyor_door_open_angle}°")
    logger.info(f"Bin door angles: closed={bin_door_closed_angle}°, open={bin_door_open_angle}°")

    # Collect all servos from the IRL system
    servos = []

    for dm_idx, distribution_module in enumerate(irl_system["distribution_modules"]):
        # Add conveyor door servo
        servos.append({
            "servo": distribution_module.servo,
            "name": f"DM{dm_idx}_ConveyorDoor",
            "closed_angle": conveyor_door_closed_angle,
            "open_angle": conveyor_door_open_angle,
        })

        # Add bin door servos
        for bin_idx, bin_obj in enumerate(distribution_module.bins):
            servos.append({
                "servo": bin_obj.servo,
                "name": f"DM{dm_idx}_Bin{bin_idx}",
                "closed_angle": bin_door_closed_angle,
                "open_angle": bin_door_open_angle,
            })

    try:
        logger.info(f"Starting servo test with {len(servos)} servos...")

        while True:
            # Set all servos to closed position
            logger.info("Setting all servos to CLOSED position")
            for servo_config in servos:
                logger.info(f"  {servo_config['name']}: {servo_config['closed_angle']}°")
                servo_config["servo"].setAngle(servo_config["closed_angle"])

            time.sleep(30)

            #Set all servos to open position
            logger.info("Setting all servos to OPEN position")
            for servo_config in servos:
                logger.info(f"  {servo_config['name']}: {servo_config['open_angle']}°")
                servo_config["servo"].setAngle(servo_config["open_angle"])

            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during test: {e}")
    finally:
        logger.info("Returning all servos to closed position...")
        for servo_config in servos:
            servo_config["servo"].setAngle(servo_config["closed_angle"])

        logger.info("Cleaning up...")
        irl_system["arduino"].flush()
        irl_system["arduino"].close()
        logger.info("Test complete")


if __name__ == "__main__":
    main()
