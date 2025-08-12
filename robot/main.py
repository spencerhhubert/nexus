import time
import cv2
import os
import threading
import uvicorn
from robot.irl.config import buildIRLSystemInterface, IRLSystemInterface, buildIRLConfig
from robot.irl.motors import Servo, DCMotor
from robot.global_config import GlobalConfig, buildGlobalConfig
from robot.controller import SortingController


def main() -> None:
    gc = buildGlobalConfig()
    irl_config = buildIRLConfig()
    system: IRLSystemInterface = buildIRLSystemInterface(irl_config, gc)

    logger = gc["logger"]
    logger.info(f"Running with debug level: {gc['debug_level']}")

    sorting_controller = SortingController(gc, system)

    def run_server():
        uvicorn.run(
            sorting_controller.api_server.app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
        )

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    logger.info("FastAPI server started on http://localhost:8080")

    try:
        sorting_controller.initialize()
        sorting_controller.startHardware()
        sorting_controller.run()
    except KeyboardInterrupt:
        logger.info("Interrupt received in main...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        sorting_controller.stop()


if __name__ == "__main__":
    main()
