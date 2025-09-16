import sys
import time
import cv2
from ultralytics import YOLO
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface


def main():
    gc = buildGlobalConfig()
    logger = gc["logger"]

    logger.info("Building IRL configuration...")
    irl_config = buildIRLConfig()

    logger.info("Connecting to cameras...")
    irl_system = buildIRLSystemInterface(irl_config, gc)

    logger.info("Loading YOLO models...")
    model_path = gc["yolo_weights_path"] if gc["yolo_weights_path"] else gc["yolo_model"]
    main_yolo = YOLO(model_path)
    feeder_yolo = YOLO(model_path)

    main_camera = irl_system["main_camera"]
    feeder_camera = irl_system["feeder_camera"]

    logger.info("Starting YOLO tracking loop...")

    try:
        frame_count = 0

        while True:
            frame_count += 1

            main_frame = main_camera.captureFrame()
            if main_frame is not None:
                logger.info(f"Frame {frame_count}: Tracking main camera frame...")
                main_results = main_yolo.track(main_frame, persist=True, tracker="botsort.yaml")

                if main_results and len(main_results) > 0:
                    annotated_main = main_results[0].plot()
                    cv2.imshow("Main Camera YOLO Tracking", annotated_main)

            feeder_frame = feeder_camera.captureFrame()
            if feeder_frame is not None:
                logger.info(f"Frame {frame_count}: Tracking feeder camera frame...")
                feeder_results = feeder_yolo.track(feeder_frame, persist=True, tracker="botsort.yaml")

                if feeder_results and len(feeder_results) > 0:
                    annotated_feeder = feeder_results[0].plot()
                    cv2.imshow("Feeder Camera YOLO Tracking", annotated_feeder)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            time.sleep(0.1)

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