# services/s3_service.py
"""
S3 helper - uploads files, generates presigned urls.
Works with AWS S3 or MinIO (set S3_ENDPOINT_URL in .env).
"""

import boto3
from botocore.client import Config
import os
from typing import Optional
import logging
from datetime import timedelta

import config

logger = logging.getLogger("smartx_bot.s3_service")

# lazy client
_s3_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client:
        return _s3_client
    endpoint = os.getenv("S3_ENDPOINT_URL", None)
    access = os.getenv("S3_ACCESS_KEY", None)
    secret = os.getenv("S3_SECRET_KEY", None)
    region = os.getenv("S3_REGION", "us-east-1")
    # If using MinIO, endpoint must be provided and signature_version may be required
    config_options = {}
    if endpoint:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access,
            aws_secret_access_key=secret,
            config=Config(signature_version="s3v4"),
            region_name=region,
        )
    else:
        # default AWS
        _s3_client = boto3.client("s3", region_name=region)
    return _s3_client

def ensure_bucket(bucket_name: str):
    s3 = _get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except Exception:
        try:
            s3.create_bucket(Bucket=bucket_name)
            return True
        except Exception as e:
            logger.exception("Failed to ensure bucket %s: %s", bucket_name, e)
            return False

def upload_file(local_path: str, object_name: Optional[str] = None, bucket: Optional[str] = None) -> Optional[str]:
    """
    Upload local file to S3 and return object key or None on error.
    """
    s3 = _get_s3_client()
    bucket = bucket or os.getenv("S3_BUCKET")
    if not bucket:
        raise RuntimeError("S3_BUCKET not configured")
    if not object_name:
        object_name = os.path.basename(local_path)
    try:
        # ensure bucket exists
        ensure_bucket(bucket)
        s3.upload_file(local_path, bucket, object_name)
        logger.info("Uploaded %s to s3://%s/%s", local_path, bucket, object_name)
        return object_name
    except Exception as e:
        logger.exception("S3 upload failed: %s", e)
        return None

def generate_presigned_url(object_name: str, expires_in_seconds: int = 3600, bucket: Optional[str] = None) -> Optional[str]:
    """
    Generate presigned GET URL for object.
    """
    s3 = _get_s3_client()
    bucket = bucket or os.getenv("S3_BUCKET")
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": object_name},
            ExpiresIn=expires_in_seconds,
        )
        return url
    except Exception as e:
        logger.exception("Failed to create presigned url: %s", e)
        return None
