import time
import os
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface

DELAY_MS = 250


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

    logger.info(
        f"Conveyor door angles: closed={conveyor_door_closed_angle}°, open={conveyor_door_open_angle}°"
    )
    logger.info(
        f"Bin door angles: closed={bin_door_closed_angle}°, open={bin_door_open_angle}°"
    )

    def open_doors_sequence():
        logger.info("=== OPENING DOORS SEQUENCE ===")

        for dm_idx, distribution_module in enumerate(irl_system["distribution_modules"]):
            # Open conveyor door first
            logger.info(f"Opening DM{dm_idx} conveyor door to {conveyor_door_open_angle}°")
            distribution_module.servo.setAngle(conveyor_door_open_angle)
            time.sleep(DELAY_MS / 1000.0)

            # Open bin doors in descending channel order (highest first)
            bin_indices = list(range(len(distribution_module.bins)))
            bin_indices.reverse()  # Highest channel first

            for bin_idx in bin_indices:
                logger.info(f"Opening DM{dm_idx} bin {bin_idx} door to {bin_door_open_angle}°")
                distribution_module.bins[bin_idx].servo.setAngle(bin_door_open_angle)
                time.sleep(DELAY_MS / 1000.0)

    def close_doors_sequence():
        logger.info("=== CLOSING DOORS SEQUENCE (REVERSE ORDER) ===")

        # Reverse the distribution modules order
        distribution_modules = list(enumerate(irl_system["distribution_modules"]))
        distribution_modules.reverse()

        for dm_idx, distribution_module in distribution_modules:
            # Close bin doors first (in ascending channel order - reverse of opening)
            bin_indices = list(range(len(distribution_module.bins)))

            for bin_idx in bin_indices:
                logger.info(f"Closing DM{dm_idx} bin {bin_idx} door to {bin_door_closed_angle}°")
                if bin_idx == 3:
                    continue
                distribution_module.bins[bin_idx].servo.setAngle(bin_door_closed_angle)
                time.sleep(DELAY_MS / 1000.0)

            # Close conveyor door last
            logger.info(f"Closing DM{dm_idx} conveyor door to {conveyor_door_closed_angle}°")
            distribution_module.servo.setAngle(conveyor_door_closed_angle)
            time.sleep(DELAY_MS / 1000.0)

    try:
        logger.info(f"Starting servo demo with {len(irl_system['distribution_modules'])} distribution modules...")

        # Initialize all servos to closed position
        logger.info("Initializing all servos to closed position...")
        for dm_idx, distribution_module in enumerate(irl_system["distribution_modules"]):
            distribution_module.servo.setAngle(conveyor_door_closed_angle)
            for bin_idx, bin_obj in enumerate(distribution_module.bins):
                bin_obj.servo.setAngle(bin_door_closed_angle)

        time.sleep(2)  # Wait for initialization

        while True:
            # Open sequence
            open_doors_sequence()

            logger.info("Waiting 5 seconds...")
            time.sleep(5)

            # Close sequence (reverse order)
            close_doors_sequence()

            logger.info("Waiting 5 seconds before next cycle...")
            time.sleep(5)

    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Error during demo: {e}")
    finally:
        logger.info("Returning all servos to closed position...")
        for dm_idx, distribution_module in enumerate(irl_system["distribution_modules"]):
            distribution_module.servo.setAngle(conveyor_door_closed_angle)
            for bin_idx, bin_obj in enumerate(distribution_module.bins):
                bin_obj.servo.setAngle(bin_door_closed_angle)

        logger.info("Cleaning up...")
        irl_system["arduino"].flush()
        irl_system["arduino"].close()
        logger.info("Demo complete")


if __name__ == "__main__":
    main()
