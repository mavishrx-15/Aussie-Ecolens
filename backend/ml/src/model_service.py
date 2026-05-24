import os
from pathlib import Path
from collections import Counter

import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
from megadetector.detection import run_detector_batch

from dotenv import load_dotenv
from classes import CLASSES

import logging
import warnings

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)


class WildlifeModelService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent

        load_dotenv(self.base_dir / ".env")

        self.label_metadata = self._load_label_metadata()

        self.md_model_path = self._resolve_model_path(
            env_key="MD_MODEL_PATH",
            default_relative_path="models/mdv5a.pt"
        )

        self.species_model_path = self._resolve_model_path(
            env_key="SPECIES_MODEL_PATH",
            default_relative_path="models/model.pt"
        )

        self.device = self._get_device()
        self.species_model = self._load_species_model()

        self.transform = transforms.Compose([
            transforms.Resize((480, 480)),
            transforms.ToTensor(),
        ])

    def _resolve_model_path(self, env_key, default_relative_path):
        path_value = os.environ.get(env_key, default_relative_path)
        path = Path(path_value)

        if not path.is_absolute():
            path = self.base_dir / path

        return str(path.resolve())

    def _get_device(self):
        if torch.cuda.is_available():
            return "cuda"

        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"

        return "cpu"

    def _load_species_model(self):
        if not Path(self.species_model_path).exists():
            raise FileNotFoundError(
                f"Species model not found at: {self.species_model_path}"
            )

        model = torch.load(
            self.species_model_path,
            map_location=self.device,
            weights_only=False
        )

        model.eval()
        model.to(self.device)

        return model

    def _load_label_metadata(self):
        labels_path_value = os.environ.get(
            "LABELS_PATH",
            "labels.txt"
        )

        labels_path = Path(labels_path_value)

        if not labels_path.is_absolute():
            labels_path = self.base_dir / labels_path

        labels_path = labels_path.resolve()

        print(f"Loading labels from: {labels_path}")

        if not labels_path.exists():
            print("labels.txt not found")
            return {}

        mapping = {}

        with open(labels_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = [p.strip() for p in line.strip().split(";")]

                if len(parts) < 7:
                    continue

                _, _, _, _, genus, species, common_name = parts

                scientific_name = f"{genus}_{species}".lower()

                mapping[scientific_name] = {
                    "common_name": common_name.lower(),
                    "scientific_name": scientific_name
                }

        print(f"Loaded {len(mapping)} label mappings")

        return mapping


    def _format_tag(self, scientific_name, count):
        metadata = self.label_metadata.get(
            scientific_name,
            {
                "common_name": scientific_name.lower(),
                "scientific_name": scientific_name
            }
        )

        return {
            "common_name": metadata["common_name"],
            "scientific_name": metadata["scientific_name"],
            "count": count,
            "source": "ml"
        }

    def detect_animals(self, image_paths):
        if not Path(self.md_model_path).exists():
            raise FileNotFoundError(
                f"MegaDetector model not found at: {self.md_model_path}"
            )

        image_paths = [str(Path(path).resolve()) for path in image_paths]

        return run_detector_batch.load_and_run_detector_batch(
            image_file_names=image_paths,
            model_file=self.md_model_path,
            quiet=True
        )

    def crop_detection(self, image_path, bbox, crop_size=600):
        img = Image.open(image_path).convert("RGB")
        width, height = img.size

        x, y, w, h = bbox

        left = int(x * width)
        top = int(y * height)
        right = int((x + w) * width)
        bottom = int((y + h) * height)

        crop = img.crop((left, top, right, bottom))
        crop = crop.resize((crop_size, crop_size), Image.BILINEAR)

        return crop

    @torch.no_grad()
    def classify_crop(self, crop):
        img = self.transform(crop)
        img = img.unsqueeze(0)
        img = img.permute(0, 2, 3, 1)
        img = img.to(self.device)

        logits = self.species_model(img)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

        best_idx = int(np.argmax(probs))

        return {
            "species": CLASSES[best_idx].lower(),
            "confidence": float(probs[best_idx])
        }

    def process_image(self, image_path, confidence_threshold=0.7):
        image_path = Path(image_path).resolve()

        if not image_path.exists():
            raise FileNotFoundError(f"Image not found at: {image_path}")

        detections_data = self.detect_animals([str(image_path)])

        results = []

        for entry in detections_data:
            for detection in entry.get("detections", []):
                if detection["category"] != "1":
                    continue

                if detection["conf"] < confidence_threshold:
                    continue

                crop = self.crop_detection(
                    image_path=entry["file"],
                    bbox=detection["bbox"]
                )

                prediction = self.classify_crop(crop)

                scientific_name = prediction["species"]

                metadata = self.label_metadata.get(
                    scientific_name,
                    {
                        "common_name": scientific_name.lower(),
                        "scientific_name": scientific_name
                    }
                )

                results.append({
                    "bbox": detection["bbox"],
                    "detection_confidence": detection["conf"],
                    "common_name": metadata["common_name"],
                    "scientific_name": metadata["scientific_name"],
                    "species_confidence": prediction["confidence"]
                })

        tag_counts = Counter([r["common_name"] for r in results])

        tags = [
            {
                "common_name": common_name,
                "scientific_name": next(
                    r["scientific_name"]
                    for r in results
                    if r["common_name"] == common_name
                ),
                "count": count,
                "source": "ml"
            }
            for common_name, count in tag_counts.items()
        ]

        return {
            "file": image_path.name,
            "detections": results,
            "tags": tags,
            "tag_names": list(tag_counts.keys())
        }