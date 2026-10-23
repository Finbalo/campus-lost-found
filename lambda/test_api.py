import os
import sys

os.environ.update(
    TABLE="t", PHOTO_BUCKET="b", CDN_URL="https://cdn.example", TOPIC_ARN="arn:aws:sns:eu-west-1:1:t",
    AWS_DEFAULT_REGION="eu-west-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
)
sys.path.insert(0, os.path.dirname(__file__))
import api  # noqa: E402


def test_rejects_bad_type():
    res = api.create_item({"type": "stolen", "category": "keys", "title": "a", "location": "b", "contact": "c"})
    assert res["statusCode"] == 400


def test_rejects_missing_fields():
    res = api.create_item({"type": "lost", "category": "keys", "title": "", "location": "b", "contact": "c"})
    assert res["statusCode"] == 400


def test_rejects_bad_photo_key():
    res = api.create_item(
        {"type": "lost", "category": "keys", "title": "a", "location": "b", "contact": "c", "photoKey": "../etc/passwd"}
    )
    assert res["statusCode"] == 400


def test_upload_url_rejects_non_image():
    assert api.upload_url({"contentType": "text/html"})["statusCode"] == 400
