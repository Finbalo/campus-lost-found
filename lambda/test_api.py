import os
import sys
from types import SimpleNamespace

os.environ.update(
    TABLE="t", PHOTO_BUCKET="b", CDN_URL="https://cdn.example", TOPIC_ARN="arn:aws:sns:eu-west-1:1:t",
    AWS_DEFAULT_REGION="eu-west-1", AWS_ACCESS_KEY_ID="x", AWS_SECRET_ACCESS_KEY="x",
)
sys.path.insert(0, os.path.dirname(__file__))
import api  # noqa: E402

GOOD = {"type": "lost", "category": "keys", "title": "a", "location": "b", "contact": "c"}


def test_rejects_bad_type():
    res = api.create_item({**GOOD, "type": "stolen"}, "user-1")
    assert res["statusCode"] == 400


def test_rejects_missing_fields():
    res = api.create_item({**GOOD, "title": ""}, "user-1")
    assert res["statusCode"] == 400


def test_rejects_bad_photo_key():
    res = api.create_item({**GOOD, "photoKey": "../etc/passwd"}, "user-1")
    assert res["statusCode"] == 400


def test_upload_url_rejects_non_image():
    assert api.upload_url({"contentType": "text/html"})["statusCode"] == 400


def test_protected_route_needs_login():
    event = {"routeKey": "POST /items", "body": "{}"}
    assert api.handler(event, None)["statusCode"] == 401


def test_only_owner_can_resolve(monkeypatch):
    class Denied(Exception):
        pass

    exceptions = SimpleNamespace(ConditionalCheckFailedException=Denied)

    class FakeTable:
        meta = SimpleNamespace(client=SimpleNamespace(exceptions=exceptions))

        def update_item(self, **kwargs):
            raise Denied()

    monkeypatch.setattr(api, "table", FakeTable())
    assert api.resolve_item("abc", "someone-else")["statusCode"] == 403
