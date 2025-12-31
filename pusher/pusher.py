import os
import sys
import time
import uuid
import psycopg2
from pathlib import Path
from loguru import logger
from PIL import Image
import io

# Configure Loguru
logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)

# Configuration
# Use coherent PUSHER_ prefix; fall back to shared names
STORAGE_PATH = "./uploads"
POLL_INTERVAL = int(os.getenv("PUSHER_POLL_INTERVAL", "5"))

# Database Configuration
DB_HOST = os.getenv("PUSHER_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
DB_PORT = os.getenv("PUSHER_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("PUSHER_DB_NAME", os.getenv("POSTGRES_DB", "imagomortis"))
DB_USER = os.getenv("PUSHER_DB_USER", os.getenv("POSTGRES_USER", "postgres"))
DB_PASSWORD = os.getenv(
    "PUSHER_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "postgres")
)


def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def init_db():
    """Ensure the target table exists."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Create table if it doesn't exist
        # We store the UUID and the raw image data (BYTEA)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id UUID PRIMARY KEY,
                data BYTEA,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        # Add new columns if they don't exist
        cur.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS image_resolution TEXT")
        cur.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS size BIGINT")
        cur.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS job JSONB")
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Database initialized/verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # We might want to retry or exit. For now, let's exit so k8s/docker restarts us.
        sys.exit(1)


def process_image(file_path: Path):
    """Process a single image file."""
    file_uuid = None
    try:
        # 1. Parse UUID from filename
        # Filename format expected: {uuid}.jpg
        try:
            file_uuid_str = file_path.stem
            file_uuid = uuid.UUID(file_uuid_str)
        except ValueError:
            logger.warning(f"Skipping file with invalid UUID format: {file_path.name}")
            return

        logger.info(f"Processing file: {file_path.name}", uuid=str(file_uuid))

        # 2. Read file content
        with open(file_path, "rb") as f:
            image_data = f.read()

        # 3. Calculate image resolution and size
        size = len(image_data)
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        resolution = f"{width}x{height}"

        # 4. Upload to Postgres
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            # Insert or do nothing if already exists (idempotency)
            cur.execute(
                "INSERT INTO images (id, data, image_resolution, size) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (str(file_uuid), image_data, resolution, size),
            )
            conn.commit()
            logger.info(f"Uploaded image to DB", uuid=str(file_uuid))

            # 4. Delete file from folder
            os.remove(file_path)
            logger.info(f"Deleted local file: {file_path.name}", uuid=str(file_uuid))

        except Exception as db_err:
            conn.rollback()
            raise db_err
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        logger.error(
            f"Failed to process file {file_path.name}: {str(e)}",
            uuid=str(file_uuid) if file_uuid else None,
        )


def main():
    logger.info("Pusher service starting up")

    # Ensure storage directory exists
    storage_path = Path(STORAGE_PATH)
    if not storage_path.exists():
        logger.info(f"Creating storage path: {STORAGE_PATH}")
        storage_path.mkdir(parents=True, exist_ok=True)

    # Initialize DB
    init_db()

    logger.info(f"Monitoring folder: {STORAGE_PATH}")

    while True:
        try:
            # List files in the directory
            # We only care about files, and maybe specific extensions if needed.
            # The uploader saves as .jpg, but we can be generic or specific.
            files = [f for f in storage_path.iterdir() if f.is_file()]

            for file_path in files:
                # Filter for likely image files if needed, or just try to process everything
                if file_path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    process_image(file_path)

            # Sleep before next poll
            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Stopping pusher service")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
