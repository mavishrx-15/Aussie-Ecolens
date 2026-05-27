import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SRC_DIR))

from model_service import WildlifeModelService

BASE_DIR = SRC_DIR.parent
input_dir = BASE_DIR / "src" / "test" / "images"

image_files = [
    str(path)
    for path in input_dir.iterdir()
    if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
]

model_service = WildlifeModelService()

for image_path in image_files:
    result = model_service.process_image(image_path)
    print(result)