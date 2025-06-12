import requests
from robot.global_config import GlobalConfig, buildGlobalConfig
from robot.piece.bricklink.auth import mkAuth


def generateBricklinkData(global_config: GlobalConfig) -> None:
    logger = global_config["logger"]

    logger.info("Starting BrickLink data generation...")

    try:
        auth = mkAuth()
        logger.info("BrickLink authentication configured successfully")

        # Make a simple test request to verify authentication
        base_url = "https://api.bricklink.com/api/store/v1"
        test_endpoint = "/colors"

        logger.info("Making test request to BrickLink API...")
        response = requests.get(base_url + test_endpoint, auth=auth)

        if response.status_code == 200:
            data = response.json()
            color_count = len(data.get("data", []))
            logger.info(f"BrickLink API test successful - found {color_count} colors")
        else:
            logger.error(f"BrickLink API test failed with status {response.status_code}: {response.text}")
            return

        # TODO: Call individual generation scripts
        # generateCategories(global_config, auth)
        # generateKinds(global_config, auth)
        # generateColors(global_config, auth)

        logger.info("BrickLink data generation completed")

    except Exception as e:
        logger.error(f"Failed to generate BrickLink data: {e}")
        raise


def main() -> None:
    global_config = buildGlobalConfig()
    generateBricklinkData(global_config)


if __name__ == "__main__":
    main()
