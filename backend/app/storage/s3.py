"""S3 / S3-compatible storage wrapper (boto3)."""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config

from ..config import get_settings


def is_s3_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.AWS_ACCESS_KEY_ID
        and settings.AWS_SECRET_ACCESS_KEY
        and settings.S3_BUCKET_NAME
    )


def _client():
    if not is_s3_configured():
        return None
    settings = get_settings()
    kwargs = dict(
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )
    if settings.S3_ENDPOINT_URL:
        kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    return boto3.client("s3", **kwargs)


def upload_file(local_path: Path, s3_key: str) -> None:
    """Upload a local file to S3 under the given key."""
    if not is_s3_configured():
        return
    settings = get_settings()
    cl = _client()
    if cl:
        cl.upload_file(str(local_path), settings.S3_BUCKET_NAME, s3_key)


def upload_bytes(data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> None:
    if not is_s3_configured():
        return
    settings = get_settings()
    cl = _client()
    if cl:
        cl.put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )


def generate_presigned_url(s3_key: str, expires_in: int = 3600) -> str | None:
    """Return a pre-signed GET URL for the given S3 object key."""
    if not is_s3_configured() or not s3_key:
        return None
    settings = get_settings()
    cl = _client()
    if not cl:
        return None
    try:
        return cl.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
            ExpiresIn=expires_in,
        )
    except Exception:
        return None


def delete_objects(s3_keys: list[str]) -> None:
    settings = get_settings()
    if not s3_keys:
        return
    cl = _client()
    cl.delete_objects(
        Bucket=settings.S3_BUCKET_NAME,
        Delete={"Objects": [{"Key": k} for k in s3_keys]},
    )
