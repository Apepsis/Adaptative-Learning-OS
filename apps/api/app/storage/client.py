import asyncio
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import Config as BotoConfig

from app.core.config import Settings, get_settings


class StorageClient:
    """Thin async-friendly wrapper around an S3-compatible object store.

    Uses boto3 (sync) under the hood, offloaded to a thread per call. At this
    project's scale (single user, request-time uploads of a handful of
    files) that is simpler and more robust than an async S3 client, and
    keeps the FastAPI event loop unblocked during network I/O.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def upload_fileobj(
        self, *, bucket: str, key: str, fileobj: BinaryIO, content_type: str
    ) -> None:
        await asyncio.to_thread(
            self._client.upload_fileobj,
            fileobj,
            bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )

    async def delete_object(self, *, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=bucket, Key=key)

    async def object_exists(self, *, bucket: str, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=bucket, Key=key)
            return True
        except self._client.exceptions.ClientError:
            return False

    def generate_presigned_get_url(self, *, bucket: str, key: str, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    async def list_buckets(self) -> list[str]:
        response = await asyncio.to_thread(self._client.list_buckets)
        return [b["Name"] for b in response.get("Buckets", [])]

    async def ensure_bucket(self, bucket: str) -> None:
        """Idempotently create a bucket. Used by tests and local bootstrap;
        production deployments should provision buckets via infrastructure,
        not on the request/import path."""
        try:
            await asyncio.to_thread(self._client.create_bucket, Bucket=bucket)
        except self._client.exceptions.BucketAlreadyOwnedByYou:
            pass
        except self._client.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "BucketAlreadyExists":
                raise


@lru_cache
def get_storage_client() -> StorageClient:
    return StorageClient(get_settings())
