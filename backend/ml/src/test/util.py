from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent

def draw_detections(selected_image, result):
    # Create output folder
    output_dir = BASE_DIR / "output_images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Open original image
    img = Image.open(selected_image).convert("RGB")
    draw = ImageDraw.Draw(img)

    W, H = img.size

    # Draw detections
    for detection in result["detections"]:
        x, y, w, h = detection["bbox"]

        left = int(x * W)
        top = int(y * H)
        right = int((x + w) * W)
        bottom = int((y + h) * H)

        species = detection.get("common_name") or detection.get("scientific_name") or "unknown"
        confidence = detection["species_confidence"]

        # Draw rectangle
        draw.rectangle(
            [left, top, right, bottom],
            outline="red",
            width=4
        )

        # Draw label
        label = f"{species} ({confidence:.2f})"

        draw.text(
            (left, max(0, top - 20)),
            label,
            fill="red"
        )

    # Save output image
    output_path = output_dir / f"output_{Path(selected_image).name}"

    img.save(output_path)

    print(f"\nSaved output image to:\n{output_path}")