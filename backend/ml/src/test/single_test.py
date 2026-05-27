import sys
from pathlib import Path
import json
from util import draw_detections

SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

from model_service import WildlifeModelService

BASE_DIR = SRC_DIR.parent
input_dir = BASE_DIR / "src" / "test" / "images"

# Get all valid image files
image_files = [
    path for path in input_dir.iterdir()
    if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
]

# Display selectable list
print("\nAvailable Images:\n")

for idx, image_path in enumerate(image_files, start=1):
    print(f"[{idx}] {image_path.name}")

# User selection
selection = int(input("\nSelect an image number: "))

# Validate selection
if selection < 1 or selection > len(image_files):
    print("Invalid selection.")
    sys.exit(1)

selected_image = image_files[selection - 1]

print(f"\nProcessing: {selected_image.name}\n")

# Run model
model_service = WildlifeModelService()

result = model_service.process_image(selected_image)
draw_detections(selected_image, result)
print('\nRESULT:')
print(json.dumps(result, indent=4))