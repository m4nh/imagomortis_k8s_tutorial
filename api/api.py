import os
import psycopg2
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import sys
from loguru import logger
import json

# Configure Loguru
logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)

# Configuration - using similar env vars as pusher.py for consistency
DB_HOST = os.getenv(
    "API_DB_HOST", os.getenv("PUSHER_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
)
DB_PORT = os.getenv(
    "API_DB_PORT", os.getenv("PUSHER_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
)
DB_NAME = os.getenv(
    "API_DB_NAME", os.getenv("PUSHER_DB_NAME", os.getenv("POSTGRES_DB", "imagomortis"))
)
DB_USER = os.getenv(
    "API_DB_USER", os.getenv("PUSHER_DB_USER", os.getenv("POSTGRES_USER", "postgres"))
)
DB_PASSWORD = os.getenv(
    "API_DB_PASSWORD",
    os.getenv("PUSHER_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "postgres")),
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Allows all origins; replace with specific domains in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class Image(BaseModel):
    id: str
    created_at: Optional[str] = None
    resolution: Optional[str] = None
    size: Optional[str] = None
    job: Optional[Dict[str, Any]] = None


def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


@app.get("/images", response_model=List[Image])
async def get_images():
    """List all images stored in the database."""
    logger.info("Endpoint called: GET /images")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, created_at, image_resolution, size, job FROM images ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        # Return list of dicts with id and created_at
        images = [
            {
                "id": str(row[0]),
                "created_at": row[1].isoformat() if row[1] else None,
                "resolution": row[2],
                "size": str(row[3]),
                "job": row[4],
            }
            for row in rows
        ]
        logger.info(f"Retrieved {len(images)} images")
        return images
    except Exception as e:
        logger.error(f"Error retrieving images: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/images/{image_id}")
async def get_image(image_id: str):
    """Retrieve the image content by ID."""
    logger.info(f"Endpoint called: GET /images/{image_id}")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT data FROM images WHERE id = %s", (image_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row is None:
            logger.warning(f"Image not found: {image_id}")
            raise HTTPException(status_code=404, detail="Image not found")
        image_data = row[0]
        logger.info(f"Retrieved image: {image_id}, size: {len(image_data)} bytes")
        return Response(content=image_data, media_type="image/jpeg")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving image {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_config=None)
