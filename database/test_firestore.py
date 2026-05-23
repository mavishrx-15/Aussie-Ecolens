import os
from google.cloud import firestore

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "database/aussie-ecolens-497114-b21fbf6e38e7.json"

db = firestore.Client(database="aussie-ecolens")

# Write test
doc_ref = db.collection("media_files").document("test001")
doc_ref.set({
    "url": "s3://bucket/test.jpg",
    "thumbnail_url": "s3://bucket/thumb_test.jpg",
    "type": "image",
    "checksum": "md5:abc123",
    "tags": {"koala": 3, "magpie": 1},
    "uploaded_at": "2026-05-23"
})
print("Write successful")

# Read test
doc = doc_ref.get()
print("Read successful:", doc.to_dict())