# Image Task

This directory contains scripts for image processing tasks.

## Draw Circles Script

`draw_circles.py` is a Typer CLI script that loads an image, draws random white circles on it, and saves the result.

### Usage

First, install dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
python draw_circles.py path/to/input/image.jpg path/to/output/image.jpg
```

The script will draw 10 random white filled circles on the image and save it to the output path.

### Requirements

- Python 3.7+
- typer
- opencv-python

### Troubleshooting

- Ensure the input image exists and is a valid image file.
- The output path should be writable.
- If you get import errors, install the requirements.