import boto3
import os
from google.cloud import firestore
from collections import defaultdict

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "database/aussie-ecolens-497114-b21fbf6e38e7.json"

dynamodb = boto3.resource("dynamodb", region_name="ap-southeast-2")
table = dynamodb.Table("media_files")
db = firestore.Client(database="aussie-ecolens")

def sync():
    response = table.scan()
    items = response.get("Items", [])
    
    for item in items:
        file_id = item.get("file_id")
        tag_names = item.get("tag_names", [])
        
        if not tag_names:
            detections = item.get("detections", [])
            counts = defaultdict(int)
            for d in detections:
                name = d.get("common_name", "").lower()
                if name:
                    counts[name] += 1
            tag_names = list(counts.keys())
        
        db.collection("media_files").document(file_id).set({
            "file_id": file_id,
            "file_type": item.get("file_type"),
            "tag_names": tag_names,
            "uploaded_at": item.get("uploaded_at"),
        })
        print(f"Synced {file_id}: {tag_names}")

sync()
print("Sync complete!")