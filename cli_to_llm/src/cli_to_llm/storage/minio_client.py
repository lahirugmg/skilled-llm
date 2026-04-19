"""MinIO client for managing LLM wiki and context files."""

from __future__ import annotations

import io
import os
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error


class MinIOClient:
    """Client for interacting with MinIO S3-compatible storage."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        secure: bool = False,
    ):
        """Initialize MinIO client.

        Args:
            endpoint: MinIO server endpoint (default: localhost:9000)
            access_key: MinIO access key (default: minioadmin)
            secret_key: MinIO secret key (default: minioadmin)
            secure: Use HTTPS if True (default: False)
        """
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ROOT_USER", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
        self.secure = secure

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket(self, bucket_name: str) -> None:
        """Ensure bucket exists, create if not.

        Args:
            bucket_name: Name of the bucket to ensure exists
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as exc:
            raise RuntimeError(f"Failed to ensure bucket {bucket_name}: {exc}") from exc

    def upload_file(
        self,
        bucket_name: str,
        object_name: str,
        file_data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload file to MinIO.

        Args:
            bucket_name: Target bucket name
            object_name: Object name/path in bucket
            file_data: File content as bytes or file-like object
            content_type: MIME type of the file
            metadata: Optional metadata to attach to the object

        Returns:
            Object name (path) of uploaded file

        Raises:
            RuntimeError: If upload fails
        """
        try:
            self.ensure_bucket(bucket_name)

            if isinstance(file_data, bytes):
                file_data = io.BytesIO(file_data)
                length = len(file_data.getvalue())
            else:
                file_data.seek(0, 2)  # Seek to end
                length = file_data.tell()
                file_data.seek(0)  # Reset to beginning

            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=length,
                content_type=content_type,
                metadata=metadata,
            )
            return object_name
        except S3Error as exc:
            raise RuntimeError(f"Failed to upload file {object_name}: {exc}") from exc

    def download_file(self, bucket_name: str, object_name: str) -> bytes:
        """Download file from MinIO.

        Args:
            bucket_name: Source bucket name
            object_name: Object name/path in bucket

        Returns:
            File content as bytes

        Raises:
            RuntimeError: If download fails
        """
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as exc:
            raise RuntimeError(f"Failed to download file {object_name}: {exc}") from exc

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        """List objects in bucket with optional prefix filter.

        Args:
            bucket_name: Bucket to list objects from
            prefix: Optional prefix to filter objects

        Returns:
            List of object names

        Raises:
            RuntimeError: If listing fails
        """
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as exc:
            raise RuntimeError(f"Failed to list objects in {bucket_name}: {exc}") from exc

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete object from MinIO.

        Args:
            bucket_name: Bucket containing the object
            object_name: Object name/path to delete

        Raises:
            RuntimeError: If deletion fails
        """
        try:
            self.client.remove_object(bucket_name, object_name)
        except S3Error as exc:
            raise RuntimeError(f"Failed to delete object {object_name}: {exc}") from exc

    def get_object_metadata(self, bucket_name: str, object_name: str) -> dict[str, str]:
        """Get object metadata.

        Args:
            bucket_name: Bucket containing the object
            object_name: Object name/path

        Returns:
            Dictionary of metadata

        Raises:
            RuntimeError: If retrieval fails
        """
        try:
            stat = self.client.stat_object(bucket_name, object_name)
            return {
                "size": str(stat.size),
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified.isoformat() if stat.last_modified else "",
                **(stat.metadata or {}),
            }
        except S3Error as exc:
            raise RuntimeError(f"Failed to get metadata for {object_name}: {exc}") from exc
