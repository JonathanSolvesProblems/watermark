"""Frame and pack storage. Local disk by default, S3 when configured. Same
interface either way so the incident code never knows which."""
from __future__ import annotations

from pathlib import Path


class BlobStore:
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    def get(self, key: str) -> bytes:
        raise NotImplementedError

    def delete_prefix(self, prefix: str) -> int:
        raise NotImplementedError

    def local_path(self, key: str) -> Path | None:
        return None


class LocalBlobStore(BlobStore):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError("key escapes blob root")
        return p

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._p(key).read_bytes()

    def delete_prefix(self, prefix: str) -> int:
        base = self._p(prefix)
        if not base.exists():
            return 0
        n = 0
        for p in sorted(base.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
                n += 1
            elif p.is_dir():
                p.rmdir()
        if base.is_dir():
            base.rmdir()
        return n

    def local_path(self, key: str) -> Path | None:
        return self._p(key)


class S3BlobStore(BlobStore):
    """boto3 is imported lazily so `mock` mode never needs AWS installed."""

    def __init__(self, bucket: str, region: str, prefix: str = "watermark/"):
        import boto3
        self.s3 = boto3.client("s3", region_name=region)
        self.bucket = bucket
        self.prefix = prefix

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.s3.put_object(Bucket=self.bucket, Key=self.prefix + key, Body=data, ContentType=content_type,
                           ServerSideEncryption="AES256")
        return key

    def get(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=self.prefix + key)["Body"].read()

    def delete_prefix(self, prefix: str) -> int:
        paginator = self.s3.get_paginator("list_objects_v2")
        n = 0
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix + prefix):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                self.s3.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})
                n += len(objs)
        return n


def make_blob_store(settings) -> BlobStore:
    if settings.blob_backend == "s3" and settings.s3_bucket:
        return S3BlobStore(settings.s3_bucket, settings.aws_region)
    return LocalBlobStore(settings.blob_dir)
