import requests
from robot.piece.bricklink.generate_piece_config import (
    PieceGenerationConfig,
    buildPieceGenerationConfig,
)
from robot.piece.bricklink.auth import mkAuth
from robot.piece.bricklink.generate_categories import generateCategories
from robot.piece.bricklink.generate_colors import generateColors
from robot.piece.bricklink.generate_kinds import generateKinds


def generateBricklinkData(piece_config: PieceGenerationConfig) -> None:
    logger = piece_config["logger"]

    logger.info("Starting BrickLink data generation...")

    try:
        auth = mkAuth()
        logger.info("BrickLink authentication configured successfully")

        generateCategories(piece_config, auth)
        generateColors(piece_config, auth)
        generateKinds(piece_config, auth)

        logger.info("BrickLink data generation completed")

    except Exception as e:
        logger.error(f"Failed to generate BrickLink data: {e}")
        raise


def main() -> None:
    piece_config = buildPieceGenerationConfig()
    generateBricklinkData(piece_config)


if __name__ == "__main__":
    main()
