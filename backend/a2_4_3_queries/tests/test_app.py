import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import app


SAMPLE_ITEMS = ROOT / "tests" / "sample_items.json"


class QueryApiTests(unittest.TestCase):
    def setUp(self):
        app._LOCAL_ITEMS_CACHE = None
        os.environ["LOCAL_ITEMS_FILE"] = str(SAMPLE_ITEMS)
        os.environ["MEDIA_BUCKET"] = "fit5225-demo-bucket"
        os.environ.pop("TABLE_NAME", None)
        os.environ.pop("PUBLIC_BASE_URL", None)
        os.environ.pop("TAGGER_FUNCTION_NAME", None)

    def call_api(self, path, body, method="POST"):
        response = app.lambda_handler(
            {
                "path": path,
                "httpMethod": method,
                "body": json.dumps(body),
            },
            None,
        )
        response["json"] = json.loads(response["body"])
        return response

    def test_query_by_tag_count_uses_and_and_minimum_counts(self):
        response = self.call_api("/query/tags", {"cattle": 3})
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["json"]["count"], 1)
        self.assertIn("60c9353e", response["json"]["urls"][0])

        response = self.call_api("/query/tags", {"cattle": 4})
        self.assertEqual(response["json"]["count"], 0)

        response = self.call_api("/query/tags", {"dingo": 1, "cattle": 1})
        self.assertEqual(response["json"]["count"], 0)

    def test_query_by_species_accepts_list_payload(self):
        response = self.call_api("/query/species", {"species": ["dingo"]})
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["json"]["count"], 1)
        self.assertEqual(response["json"]["results"][0]["tag_names"], ["dingo"])

    def test_query_by_thumbnail_returns_original_file_url(self):
        thumbnail_url = (
            "https://fit5225-demo-bucket.s3.amazonaws.com/"
            "thumbnails/b7b8076c-93de-49d6-976a-401369bb1d91_Canis_familiaris_1_thumb.jpg"
        )
        response = self.call_api("/query/thumbnail", {"thumbnail_url": thumbnail_url})
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("/raw/b7b8076c-93de-49d6-976a-401369bb1d91", response["json"]["full_url"])

    def test_query_by_uploaded_file_tags_can_use_detected_tags_for_demo(self):
        response = self.call_api("/query/file-tags", {"detected_tags": ["cattle"]})
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["json"]["count"], 1)
        self.assertIn("/raw/60c9353e", response["json"]["urls"][0])

    def test_bulk_add_and_remove_tag(self):
        dingo_url = (
            "https://fit5225-demo-bucket.s3.amazonaws.com/"
            "raw/b7b8076c-93de-49d6-976a-401369bb1d91_Canis_familiaris_1.JPG"
        )

        add_response = self.call_api(
            "/tags/bulk",
            {"urls": [dingo_url], "tags": ["night"], "operation": 1},
        )
        self.assertEqual(add_response["statusCode"], 200)
        self.assertTrue(add_response["json"]["updated"][0]["changed"])

        query_response = self.call_api("/query/species", {"species": ["night"]})
        self.assertEqual(query_response["json"]["count"], 1)

        remove_response = self.call_api(
            "/tags/bulk",
            {"urls": [dingo_url], "tags": ["night"], "operation": 0},
        )
        self.assertEqual(remove_response["statusCode"], 200)
        self.assertTrue(remove_response["json"]["updated"][0]["changed"])

        query_response = self.call_api("/query/species", {"species": ["night"]})
        self.assertEqual(query_response["json"]["count"], 0)

    def test_delete_removes_database_item_in_local_mode(self):
        response = self.call_api(
            "/files/delete",
            {
                "urls": [
                    "https://fit5225-demo-bucket.s3.amazonaws.com/"
                    "raw/504a6b20-a77e-4525-a168-4ca9f62d822c_Alectura_lathami_2.JPG"
                ]
            },
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["json"]["deleted_count"], 1)

        query_response = self.call_api(
            "/query/species", {"species": ["australian brushturkey"]}
        )
        self.assertEqual(query_response["json"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
