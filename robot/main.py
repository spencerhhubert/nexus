import time
import threading
import uvicorn
from robot.irl.config import buildIRLSystemInterface, buildIRLConfig
from robot.global_config import buildGlobalConfig
from robot.controller import Controller
from robot.api.server import app, init_api


def main() -> None:
    gc = buildGlobalConfig()
    irl_config = buildIRLConfig()
    irl_system = buildIRLSystemInterface(irl_config, gc)

    logger = gc["logger"]
    logger.info(f"Running with debug level: {gc['debug_level']}")

    websocket_manager = init_api(None)
    controller = Controller(gc, irl_system, websocket_manager)
    init_api(controller)

    # Start API server in separate thread
    api_thread = threading.Thread(
        target=uvicorn.run,
        args=[app],
        kwargs={"host": "0.0.0.0", "port": 8000, "log_level": "info"},
        daemon=True,
    )
    api_thread.start()

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
