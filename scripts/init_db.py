from technoshare_commentator.store.db import init_db
import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    logging.info("Initializing database...")
    init_db()
    logging.info("Database initialized.")
