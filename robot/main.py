import time
from robot.irl.config import buildIRLSystemInterface, buildIRLConfig
from robot.global_config import buildGlobalConfig
from robot.controller import Controller


def main() -> None:
    gc = buildGlobalConfig()
    irl_config = buildIRLConfig()
    irl_system = buildIRLSystemInterface(irl_config, gc)

    logger = gc["logger"]
    logger.info(f"Running with debug level: {gc['debug_level']}")

    controller = Controller(gc, irl_system)

    try:
        controller.start()
        # Keep main thread alive
        while controller.running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupt received in main...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        controller.stop()


if __name__ == "__main__":
    main()
