import sys
import time
import cv2
from robot.global_config import buildGlobalConfig
from robot.irl.config import buildIRLConfig, buildIRLSystemInterface
from robot.ai.yolo import YOLOModel


def main():
    gc = buildGlobalConfig()
    logger = gc["logger"]

    logger.info("Building IRL configuration...")
    irl_config = buildIRLConfig()

    logger.info("Connecting to cameras...")
    irl_system = buildIRLSystemInterface(irl_config, gc)

    logger.info("Loading YOLO models...")
    main_yolo = YOLOModel(gc["yolo_model"], gc["yolo_weights_path"])
    feeder_yolo = YOLOModel(gc["yolo_model"], gc["yolo_weights_path"])

    main_camera = irl_system["main_camera"]
    feeder_camera = irl_system["feeder_camera"]

    logger.info("Starting YOLO analysis loop...")

    try:
        frame_count = 0

        while True:
            frame_count += 1

            main_frame = main_camera.captureFrame()
            if main_frame is not None:
                logger.info(f"Frame {frame_count}: Tracking main camera frame...")
                main_results = main_yolo.track_frame(main_frame)

                if main_results["results"]:
                    annotated_main = main_yolo.visualize_results(
                        main_frame, main_results["results"], max_tracks=32
                    )
                    cv2.imshow("Main Camera YOLO Tracking", annotated_main)

            feeder_frame = feeder_camera.captureFrame()
            if feeder_frame is not None:
                logger.info(f"Frame {frame_count}: Tracking feeder camera frame...")
                feeder_results = feeder_yolo.track_frame(feeder_frame)

                if feeder_results["results"]:
                    annotated_feeder = feeder_yolo.visualize_results(
                        feeder_frame, feeder_results["results"], max_tracks=32
                    )
                    cv2.imshow("Feeder Camera YOLO Tracking", annotated_feeder)

            main_yolo.profiling.printProfiling()

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
