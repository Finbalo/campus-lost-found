import json
import os
import re
import time
import uuid
from decimal import Decimal

import boto3
from botocore.config import Config

REGION = os.environ.get("AWS_REGION", "eu-west-1")
table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
s3 = boto3.client("s3", region_name=REGION, config=Config(signature_version="s3v4"))
sns = boto3.client("sns")

BUCKET = os.environ["PHOTO_BUCKET"]
CDN_URL = os.environ["CDN_URL"]
TOPIC_ARN = os.environ["TOPIC_ARN"]

TYPES = {"lost", "found"}
CATEGORIES = {"phone", "id-card", "keys", "bag", "clothing", "books", "other"}
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
KEY_RE = re.compile(r"^photos/[0-9a-f]{32}\.(jpg|png|webp)$")


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body, default=lambda o: int(o) if isinstance(o, Decimal) else str(o)),
    }


def clean(value, limit):
    return str(value or "").strip()[:limit]


def list_items():
    items = table.scan().get("Items", [])
    items = [i for i in items if i.get("status") == "open"]
    items.sort(key=lambda i: i["created"], reverse=True)
    return respond(200, {"items": items[:100]})


def upload_url(body):
    ext = IMAGE_TYPES.get(body.get("contentType"))
    if not ext:
        return respond(400, {"error": "Photo must be a JPG, PNG or WebP image."})
    key = f"photos/{uuid.uuid4().hex}.{ext}"
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": BUCKET, "Key": key, "ContentType": body["contentType"]},
        ExpiresIn=300,
    )
    return respond(200, {"uploadUrl": url, "key": key})


def notify_matches(item):
    opposite = "found" if item["type"] == "lost" else "lost"
    others = table.scan().get("Items", [])
    matches = [
        o for o in others
        if o.get("status") == "open" and o["type"] == opposite and o["category"] == item["category"]
    ]
    if not matches:
        return
    lines = [f"New {item['type']} item: {item['title']} ({item['location']})", "", "Possible matches:"]
    for m in matches[:5]:
        lines.append(f"- {m['title']} at {m['location']} - contact: {m['contact']}")
    sns.publish(TopicArn=TOPIC_ARN, Subject="Lost & Found: possible match", Message="\n".join(lines))


def create_item(body, owner):
    item_type = body.get("type")
    category = body.get("category")
    title = clean(body.get("title"), 80)
    location = clean(body.get("location"), 80)
    contact = clean(body.get("contact"), 80)
    if item_type not in TYPES or category not in CATEGORIES:
        return respond(400, {"error": "Pick a valid type and category."})
    if not (title and location and contact):
        return respond(400, {"error": "Title, location and contact are required."})

    photo_key = body.get("photoKey")
    if photo_key and not KEY_RE.match(photo_key):
        return respond(400, {"error": "Invalid photo."})

    item = {
        "id": uuid.uuid4().hex,
        "type": item_type,
        "category": category,
        "title": title,
        "description": clean(body.get("description"), 300),
        "location": location,
        "contact": contact,
        "photoUrl": f"{CDN_URL}/{photo_key}" if photo_key else "",
        "status": "open",
        "ownerId": owner,
        "created": int(time.time()),
    }
    table.put_item(Item=item)
    try:
        notify_matches(item)
    except Exception as exc:  # a failed alert must never block the post
        print("notify failed:", exc)
    return respond(201, item)


def resolve_item(item_id, owner):
    try:
        table.update_item(
            Key={"id": item_id},
            UpdateExpression="SET #s = :r",
            ConditionExpression="attribute_exists(id) AND ownerId = :me",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":r": "resolved", ":me": owner},
        )
    except table.meta.client.exceptions.ConditionalCheckFailedException:
        return respond(403, {"error": "Only the person who posted this can close it."})
    return respond(200, {"ok": True})


def owner_of(event):
    claims = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    return claims.get("sub")


def handler(event, context):
    route = event["routeKey"]
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return respond(400, {"error": "Invalid JSON."})

    if route == "GET /items":
        return list_items()

    owner = owner_of(event)
    if not owner:
        return respond(401, {"error": "Please log in."})

    if route == "POST /items":
        return create_item(body, owner)
    if route == "POST /upload-url":
        return upload_url(body)
    if route == "POST /items/{id}/resolve":
        return resolve_item(event["pathParameters"]["id"], owner)
    return respond(404, {"error": "Not found."})
