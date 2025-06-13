from robot.global_config import buildGlobalConfig
from robot.storage.sqlite3.migrations import initializeDatabase


def runMigrations() -> None:
    global_config = buildGlobalConfig()
    logger = global_config["logger"]

    logger.info("Running database migrations...")
    initializeDatabase(global_config)
    logger.info("Database migrations completed successfully")


if __name__ == "__main__":
    runMigrations()
