import typer
import cv2
import random
import time
import sys
from loguru import logger

# Configure Loguru
logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)

app = typer.Typer()


@app.command()
def process_image(
    input_path: str = typer.Option(
        ..., "--input-path", help="Path to the input image file"
    ),
    output_path: str = typer.Option(
        ..., "--output-path", help="Path to save the output image file"
    ),
):
    """
    Load an image, draw random white circles on it, and save to output path.
    """
    logger.info(
        "Starting image processing", input_path=input_path, output_path=output_path
    )

    img = cv2.imread(input_path)
    if img is None:
        logger.error("Could not load image from {input_path}", input_path=input_path)
        sys.exit(1)

    # Simulate a random failure with 10% probability for testing
    if random.random() < 0.1:
        logger.error("Simulated random failure (10% chance). Exiting.")
        sys.exit(1)

    height, width = img.shape[:2]

    # Draw 15 random white circles
    total_circles = 15
    for i in range(total_circles):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        radius = random.randint(
            min(width, height) // 8, min(width, height) // 6
        )  # Ensure radius fits
        cv2.circle(img, (x, y), radius, (255, 255, 255), -1)  # White filled circle
        cv2.circle(img, (x, y), radius, (0, 0, 0), 5)  # White filled circle
        percentage = (i + 1) / total_circles * 100
        logger.info(
            f"Drew circle {i+1}/{total_circles} ({percentage:.1f}%)",
            progress={"circles": percentage},
        )
        time.sleep(1)

    cv2.imwrite(output_path, img)
    logger.info("Image processed and saved", output_path=output_path)


if __name__ == "__main__":
    app()
