import sys
import time
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface


def main():
    position = "closed"

    # Parse our arguments before buildGlobalConfig sees them
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--open":
            position = "open"
        elif arg == "--closed":
            position = "closed"
        else:
            print("Usage: python reset_servos.py [--closed|--open]")
            print("  --closed    Set all servos to closed position (default)")
            print("  --open      Set all servos to open position")
            sys.exit(1)

    # Clear sys.argv so buildGlobalConfig doesn't see our arguments
    sys.argv = [sys.argv[0]]

    gc = buildGlobalConfig()
    logger = gc["logger"]

    logger.info("Building IRL configuration...")
    irl_config = buildIRLConfig()

    logger.info("Connecting to hardware and setting up servos...")
    irl_system = buildIRLSystemInterface(irl_config, gc)

    conveyor_door_open_angle = gc["conveyor_door_open_angle"]
    conveyor_door_closed_angle = gc["conveyor_door_closed_angle"]
    bin_door_open_angle = gc["bin_door_open_angle"]
    bin_door_closed_angle = gc["bin_door_closed_angle"]

    try:
        logger.info(f"Setting all servos to {position.upper()} position...")

        for dm_idx, distribution_module in enumerate(
            irl_system["distribution_modules"]
        ):
            # Set conveyor door servo
            angle = (
                conveyor_door_open_angle
                if position == "open"
                else conveyor_door_closed_angle
            )
            logger.info(f"DM{dm_idx}_ConveyorDoor: {angle}°")
            distribution_module.servo.setAngle(angle)
            time.sleep(1)

            # Set bin door servos
            for bin_idx, bin_obj in enumerate(distribution_module.bins):
                angle = (
                    bin_door_open_angle if position == "open" else bin_door_closed_angle
                )
                logger.info(f"DM{dm_idx}_Bin{bin_idx}: {angle}°")
                bin_obj.servo.setAngle(angle)
                time.sleep(1)

        logger.info(f"All servos set to {position.upper()} position")

    except Exception as e:
        logger.error(f"Error during reset: {e}")
    finally:
        logger.info("Cleaning up...")
        irl_system["arduino"].flush()
        irl_system["arduino"].close()
        logger.info("Reset complete")


if __name__ == "__main__":
    main()
