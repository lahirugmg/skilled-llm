"""Ballerina Context Manager Agent for handling Ballerina-specific files and context."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from typing import Any

from cli_to_llm.storage import MinIOClient


class BallerinaContextManager:
    """
    Context manager for Ballerina development files.

    This agent handles:
    - Uploading Ballerina files (.bal, .toml, .md) to MinIO
    - Managing Ballerina project context (dependencies, modules, documentation)
    - Organizing files in a structured hierarchy
    - Providing file retrieval and listing capabilities
    """

    BALLERINA_BUCKET = "ballerina-context"
    SUPPORTED_EXTENSIONS = {".bal", ".toml", ".md", ".txt", ".json", ".yaml", ".yml"}

    def __init__(
        self,
        minio_endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        """Initialize the Ballerina context manager.

        Args:
            minio_endpoint: MinIO server endpoint
            access_key: MinIO access key
            secret_key: MinIO secret key
        """
        self.storage = MinIOClient(
            endpoint=minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
        )
        self.storage.ensure_bucket(self.BALLERINA_BUCKET)

    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        project_name: str = "default",
        module_name: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Upload a Ballerina-related file to MinIO.

        Args:
            file_data: File content as bytes
            filename: Name of the file
            project_name: Ballerina project name (default: "default")
            module_name: Optional module name within the project
            metadata: Additional metadata to attach

        Returns:
            Dictionary containing upload details

        Raises:
            ValueError: If file extension is not supported
            RuntimeError: If upload fails
        """
        # Validate file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension {file_ext}. "
                f"Supported: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        # Build object path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.sha256(file_data).hexdigest()[:8]

        if module_name:
            object_path = f"{project_name}/{module_name}/{timestamp}_{file_hash}_{filename}"
        else:
            object_path = f"{project_name}/{timestamp}_{file_hash}_{filename}"

        # Prepare metadata
        file_metadata = {
            "project": project_name,
            "filename": filename,
            "uploaded_at": datetime.utcnow().isoformat(),
            "file_hash": file_hash,
        }
        if module_name:
            file_metadata["module"] = module_name
        if metadata:
            file_metadata.update(metadata)

        # Determine content type
        content_type_map = {
            ".bal": "text/x-ballerina",
            ".toml": "text/x-toml",
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
        }
        content_type = content_type_map.get(file_ext, "application/octet-stream")

        # Upload to MinIO
        uploaded_path = self.storage.upload_file(
            bucket_name=self.BALLERINA_BUCKET,
            object_name=object_path,
            file_data=file_data,
            content_type=content_type,
            metadata=file_metadata,
        )

        return {
            "status": "success",
            "bucket": self.BALLERINA_BUCKET,
            "object_path": uploaded_path,
            "project": project_name,
            "module": module_name,
            "filename": filename,
            "size": len(file_data),
            "content_type": content_type,
            "uploaded_at": file_metadata["uploaded_at"],
        }

    def download_file(self, object_path: str) -> bytes:
        """Download a file from Ballerina context storage.

        Args:
            object_path: Path to the object in MinIO

        Returns:
            File content as bytes

        Raises:
            RuntimeError: If download fails
        """
        return self.storage.download_file(self.BALLERINA_BUCKET, object_path)

    def list_files(
        self,
        project_name: str | None = None,
        module_name: str | None = None,
    ) -> list[str]:
        """List files in Ballerina context storage.

        Args:
            project_name: Optional project name filter
            module_name: Optional module name filter (requires project_name)

        Returns:
            List of object paths

        Raises:
            RuntimeError: If listing fails
        """
        prefix = ""
        if project_name:
            prefix = f"{project_name}/"
            if module_name:
                prefix = f"{project_name}/{module_name}/"

        return self.storage.list_objects(self.BALLERINA_BUCKET, prefix=prefix)

    def delete_file(self, object_path: str) -> None:
        """Delete a file from Ballerina context storage.

        Args:
            object_path: Path to the object in MinIO

        Raises:
            RuntimeError: If deletion fails
        """
        self.storage.delete_object(self.BALLERINA_BUCKET, object_path)

    def get_file_metadata(self, object_path: str) -> dict[str, str]:
        """Get metadata for a file.

        Args:
            object_path: Path to the object in MinIO

        Returns:
            Dictionary of metadata

        Raises:
            RuntimeError: If retrieval fails
        """
        return self.storage.get_object_metadata(self.BALLERINA_BUCKET, object_path)

    def list_projects(self) -> list[str]:
        """List all projects in Ballerina context storage.

        Returns:
            List of project names
        """
        all_objects = self.storage.list_objects(self.BALLERINA_BUCKET)
        projects = set()
        for obj_path in all_objects:
            parts = obj_path.split("/")
            if len(parts) > 0:
                projects.add(parts[0])
        return sorted(projects)

    def get_project_summary(self, project_name: str) -> dict[str, Any]:
        """Get summary information about a project.

        Args:
            project_name: Name of the project

        Returns:
            Dictionary with project statistics and file list

        Raises:
            RuntimeError: If retrieval fails
        """
        files = self.list_files(project_name=project_name)

        # Categorize files by type
        file_types: dict[str, int] = {}
        total_size = 0

        for file_path in files:
            ext = os.path.splitext(file_path)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1

            # Get file size
            try:
                metadata = self.get_file_metadata(file_path)
                total_size += int(metadata.get("size", 0))
            except RuntimeError:
                pass  # Skip if metadata retrieval fails

        return {
            "project": project_name,
            "total_files": len(files),
            "file_types": file_types,
            "total_size_bytes": total_size,
            "files": files,
        }
