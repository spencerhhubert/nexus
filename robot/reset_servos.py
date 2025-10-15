import sys
import time
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface


def main():
    position = "closed"
    specific_bin = None

    # Parse our arguments before buildGlobalConfig sees them
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i].lower()
        if arg == "--open":
            position = "open"
            i += 1
        elif arg == "--closed":
            position = "closed"
            i += 1
        elif arg == "--bin":
            if i + 2 >= len(args):
                print("Error: --bin requires two numbers (dm_index bin_index)")
                print(
                    "Usage: python reset_servos.py [--closed|--open] [--bin DM_INDEX BIN_INDEX]"
                )
                print("  --closed    Set all servos to closed position (default)")
                print("  --open      Set all servos to open position")
                print(
                    "  --bin       Set only specific bin (e.g., --bin 0 2 for DM0 Bin2)"
                )
                sys.exit(1)
            try:
                dm_idx = int(args[i + 1])
                bin_idx = int(args[i + 2])
                specific_bin = (dm_idx, bin_idx)
                i += 3
            except ValueError:
                print("Error: --bin arguments must be integers")
                sys.exit(1)
        else:
            print(f"Unknown argument: {arg}")
            print(
                "Usage: python reset_servos.py [--closed|--open] [--bin DM_INDEX BIN_INDEX]"
            )
            print("  --closed    Set all servos to closed position (default)")
            print("  --open      Set all servos to open position")
            print("  --bin       Set only specific bin (e.g., --bin 0 2 for DM0 Bin2)")
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
        if specific_bin:
            target_dm_idx, target_bin_idx = specific_bin
            logger.info(
                f"Setting DM{target_dm_idx} Bin{target_bin_idx} to {position.upper()} position..."
            )

            if target_dm_idx >= len(irl_system["distribution_modules"]):
                logger.error(
                    f"Invalid distribution module index: {target_dm_idx} (only {len(irl_system['distribution_modules'])} modules available)"
                )
                sys.exit(1)

            distribution_module = irl_system["distribution_modules"][target_dm_idx]

            if target_bin_idx >= len(distribution_module.bins):
                logger.error(
                    f"Invalid bin index: {target_bin_idx} (only {len(distribution_module.bins)} bins available in DM{target_dm_idx})"
                )
                sys.exit(1)

            # Set conveyor door servo
            angle = (
                conveyor_door_open_angle
                if position == "open"
                else conveyor_door_closed_angle
            )
            logger.info(f"DM{target_dm_idx}_ConveyorDoor: {angle}°")
            distribution_module.servo.setAngle(angle)
            time.sleep(1)

            # Set specific bin door servo
            bin_obj = distribution_module.bins[target_bin_idx]
            angle = bin_door_open_angle if position == "open" else bin_door_closed_angle
            logger.info(f"DM{target_dm_idx}_Bin{target_bin_idx}: {angle}°")
            bin_obj.servo.setAngle(angle)
            time.sleep(1)

            logger.info(
                f"DM{target_dm_idx} Bin{target_bin_idx} set to {position.upper()} position"
            )
        else:
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
                        bin_door_open_angle
                        if position == "open"
                        else bin_door_closed_angle
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
