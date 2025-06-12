import requests
from robot.global_config import GlobalConfig, buildGlobalConfig
from robot.piece.bricklink.auth import mkAuth
from robot.piece.bricklink.generate_categories import generateCategories
from robot.piece.bricklink.generate_colors import generateColors
from robot.piece.bricklink.generate_kinds import generateKinds


def generateBricklinkData(global_config: GlobalConfig) -> None:
    logger = global_config["logger"]

    logger.info("Starting BrickLink data generation...")

    try:
        auth = mkAuth()
        logger.info("BrickLink authentication configured successfully")

        generateCategories(global_config, auth)
        generateColors(global_config, auth)
        generateKinds(global_config, auth)

        logger.info("BrickLink data generation completed")

    except Exception as e:
        logger.error(f"Failed to generate BrickLink data: {e}")
        raise


def main() -> None:
    global_config = buildGlobalConfig()
    generateBricklinkData(global_config)


if __name__ == "__main__":
    main()
