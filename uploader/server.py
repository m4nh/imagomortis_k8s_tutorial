import os
import uuid
from pathlib import Path
from io import BytesIO

from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)


def on_startup():
    logger.info("Uploader server starting up")


app = FastAPI(on_startup=[on_startup])


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend's origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables (use coherent UPLOADER_ prefix; fall back to older names for
# backwards compatibility)
STORAGE_PATH = "./uploads"
RESIZE_HEIGHT = int(
    os.getenv("UPLOADER_RESIZE_HEIGHT", os.getenv("RESIZE_HEIGHT", "256"))
)

# Host/port configuration for the Uvicorn server
UPLOADER_HOST = os.getenv("UPLOADER_HOST", "0.0.0.0")
UPLOADER_PORT = int(os.getenv("UPLOADER_PORT", "8000"))

# Ensure storage directory exists
Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)


@app.post("/upload")
async def upload_image(file: UploadFile):
    # Validate that the file is an image
    if not file.content_type or not file.content_type.startswith("image/"):
        logger.error(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail="File must be an image")

    # Generate UUID for the filename
    file_uuid = uuid.uuid4()

    logger.info(
        f"Uploading file with UUID: {file_uuid}",
        uuid=str(file_uuid),
    )

    # Create the new filename with UUID (always store as JPEG)
    new_filename = f"{file_uuid}.jpg"
    file_path = Path(STORAGE_PATH) / new_filename

    # Save the file (convert to JPEG)
    try:
        contents = await file.read()

        # Open image
        img = Image.open(BytesIO(contents))

        # Convert to RGBA to consistently handle alpha channels
        img = img.convert("RGBA")

        # Calculate new width to preserve aspect ratio
        original_width, original_height = img.size
        aspect_ratio = original_width / original_height
        new_height = RESIZE_HEIGHT
        new_width = int(new_height * aspect_ratio)

        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Prepare final RGB image for JPEG (use white background if alpha present)
        if resized_img.mode in ("RGBA", "LA") or (
            resized_img.mode == "P" and "transparency" in resized_img.info
        ):
            background = Image.new("RGB", resized_img.size, (255, 255, 255))
            alpha = resized_img.split()[-1]
            background.paste(resized_img, mask=alpha)
            final_img = background
        else:
            final_img = resized_img.convert("RGB")

        # Save as JPEG
        final_img.save(file_path, format="JPEG", quality=85)

        # log file size
        file_size = file_path.stat().st_size
        logger.info(
            f"Saved file {new_filename} ({file_size} bytes)",
            file_size=file_size,
            uuid=str(file_uuid),
            path=str(file_path),
        )

    except Exception as e:
        logger.error(f"Failed to save file: {str(e)}", uuid=str(file_uuid))
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    return JSONResponse(
        status_code=201, content={"uuid": str(file_uuid), "filename": new_filename}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=UPLOADER_HOST,
        port=UPLOADER_PORT,
        log_config=None,  # Disable uvicorn's default logging
    )
