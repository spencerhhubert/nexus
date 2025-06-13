import os
import glob
from typing import List
import argparse
from PIL import Image


def createGifFromRoute(
    route: str,
    file_extension: str,
    substring: str,
    fps: int,
    output_path: str = "output.gif",
    loop: bool = False,
) -> None:
    pattern = os.path.join(route, "**", f"*{file_extension}")
    all_files = glob.glob(pattern, recursive=True)

    filtered_files = [f for f in all_files if substring in os.path.basename(f)]

    if not filtered_files:
        print(
            f"No images found with extension '{file_extension}' and substring '{substring}' in {route}"
        )
        return

    filtered_files.sort()

    # First pass: load images and find maximum dimensions
    temp_images = []
    max_width = 0
    max_height = 0

    for file_path in filtered_files:
        try:
            img = Image.open(file_path)
            temp_images.append(img)
            max_width = max(max_width, img.width)
            max_height = max(max_height, img.height)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    if not temp_images:
        print("No valid images could be loaded")
        return

    # Second pass: letterbox/pillarbox all images to max dimensions
    images: List[Image.Image] = []
    for img in temp_images:
        # Create new canvas with max dimensions and black background
        canvas = Image.new("RGB", (max_width, max_height), (0, 0, 0))

        # Calculate position to center the image
        x_offset = (max_width - img.width) // 2
        y_offset = (max_height - img.height) // 2

        # Paste the image onto the canvas
        canvas.paste(img, (x_offset, y_offset))
        images.append(canvas)

    # Add reverse frames for ping-pong effect if loop is enabled
    if loop and len(images) > 1:
        images.extend(images[-2:0:-1])

    duration = int(1000 / fps)
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=duration,
        loop=0,
        disposal=2,
    )

    print(f"GIF created successfully: {output_path}")
    print(f"Used {len(images)} images")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a GIF from images in a directory"
    )
    parser.add_argument("route", help="Path to search for images")
    parser.add_argument(
        "--fps", type=int, default=10, help="Frames per second for the GIF"
    )
    parser.add_argument("--output", default="output.gif", help="Output GIF filename")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Create ping-pong effect by reversing frames at the end",
    )

    args = parser.parse_args()

    createGifFromRoute(
        route=args.route,
        file_extension=".jpg",
        substring="masked",
        fps=args.fps,
        output_path=args.output,
        loop=args.loop,
    )
