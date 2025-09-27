import sys
import time
import cv2
import threading
from queue import Queue
from ultralytics import YOLO
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface


def runTrackerInThread(camera, model_path, window_name, logger, result_queue):
    model = YOLO(model_path)
    frame_count = 0

    try:
        while True:
            frame_count += 1
            frame = camera.captureFrame()

            if frame is not None:
                logger.info(f"Frame {frame_count}: Tracking {window_name}...")
                results = model.track(frame, persist=True, tracker="botsort.yaml")

                if results and len(results) > 0:
                    annotated_frame = results[0].plot()
                    result_queue.put((window_name, annotated_frame))

            time.sleep(0.1)

    except Exception as e:
        logger.error(f"Error in {window_name}: {e}")


def main():
    gc = buildGlobalConfig()
    logger = gc["logger"]

    logger.info("Building IRL configuration...")
    irl_config = buildIRLConfig()

    logger.info("Connecting to cameras...")
    irl_system = buildIRLSystemInterface(irl_config, gc)

    main_camera = irl_system["main_camera"]
    feeder_camera = irl_system["feeder_camera"]

    main_model_path = (
        gc["main_camera_yolo_weights_path"]
        if gc["main_camera_yolo_weights_path"]
        else gc["yolo_model"]
    )
    feeder_model_path = (
        gc["feeder_camera_yolo_weights_path"]
        if gc["feeder_camera_yolo_weights_path"]
        else gc["yolo_model"]
    )

    logger.info("Starting threaded YOLO tracking...")

    # Create queues for thread communication
    main_queue = Queue()
    feeder_queue = Queue()

    try:
        # Create and start tracker threads
        main_thread = threading.Thread(
            target=runTrackerInThread,
            args=(
                main_camera,
                main_model_path,
                "Main Camera YOLO Tracking",
                logger,
                main_queue,
            ),
            daemon=True,
        )

        feeder_thread = threading.Thread(
            target=runTrackerInThread,
            args=(
                feeder_camera,
                feeder_model_path,
                "Feeder Camera YOLO Tracking",
                logger,
                feeder_queue,
            ),
            daemon=True,
        )

        main_thread.start()
        feeder_thread.start()

        # Handle display in main thread
        while True:
            # Display frames from queues
            try:
                if not main_queue.empty():
                    window_name, frame = main_queue.get_nowait()
                    cv2.imshow(window_name, frame)

                if not feeder_queue.empty():
                    window_name, frame = feeder_queue.get_nowait()
                    cv2.imshow(window_name, frame)

            except:
                pass

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Error during test: {e}")
    finally:
        logger.info("Cleaning up...")
        cv2.destroyAllWindows()
        irl_system["arduino"].flush()
        irl_system["arduino"].close()
        logger.info("Test complete")


if __name__ == "__main__":
    main()
