"""
S3 storage adapter for AWS Lambda deployment.
Handles PDF file storage and retrieval in S3.
"""
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import os
import hashlib
from datetime import datetime


class S3Storage:
    """
    S3 storage adapter for PDF files.

    This replaces local filesystem storage with S3 for Lambda deployment.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize S3 client.

        Args:
            bucket_name: S3 bucket name (defaults to environment variable)
        """
        self.s3_client = boto3.client('s3')
        self.bucket = bucket_name or os.environ.get('PDF_BUCKET_NAME')

        if not self.bucket:
            raise ValueError("PDF_BUCKET_NAME environment variable not set")

    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = 'application/pdf',
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to S3.

        Args:
            file_data: File content as bytes
            filename: Original filename
            content_type: MIME type
            metadata: Additional metadata to store with file

        Returns:
            S3 key (path) of uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            # Generate unique key using timestamp and hash
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            file_hash = hashlib.sha256(file_data).hexdigest()[:8]
            s3_key = f"pdfs/{timestamp}_{file_hash}_{filename}"

            # Prepare metadata (S3 only accepts string values)
            s3_metadata = {}
            if metadata:
                s3_metadata = {
                    k: str(v) for k, v in metadata.items()
                }

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata=s3_metadata,
                ServerSideEncryption='AES256'  # Encrypt at rest
            )

            return s3_key

        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {e}")

    def download_file(self, s3_key: str) -> bytes:
        """
        Download a file from S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            File content as bytes

        Raises:
            Exception: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return response['Body'].read()

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {s3_key}")
            raise Exception(f"Failed to download file from S3: {e}")

    def download_file_to_path(self, s3_key: str, local_path: str) -> str:
        """
        Download a file from S3 to local path.

        Useful for processing files that require filesystem access.

        Args:
            s3_key: S3 key (path) of the file
            local_path: Local filesystem path to save to (e.g., /tmp/file.pdf)

        Returns:
            Local path where file was saved

        Raises:
            Exception: If download fails
        """
        try:
            self.s3_client.download_file(
                Bucket=self.bucket,
                Key=s3_key,
                Filename=local_path
            )
            return local_path

        except ClientError as e:
            raise Exception(f"Failed to download file to path: {e}")

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return True

        except ClientError as e:
            print(f"Failed to delete file from S3: {e}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"Error checking file existence: {e}")

    def get_file_metadata(self, s3_key: str) -> dict:
        """
        Get metadata for a file in S3.

        Args:
            s3_key: S3 key (path) of the file

        Returns:
            Dictionary containing file metadata

        Raises:
            Exception: If file not found or error occurs
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )

            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {}),
                'etag': response.get('ETag', '').strip('"')
            }

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File not found: {s3_key}")
            raise Exception(f"Failed to get file metadata: {e}")

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        operation: str = 'get_object'
    ) -> str:
        """
        Generate a pre-signed URL for temporary file access.

        Useful for:
        - Allowing frontend to download files directly
        - Uploading files directly from browser
        - Sharing files without authentication

        Args:
            s3_key: S3 key (path) of the file
            expiration: URL expiration time in seconds (default: 1 hour)
            operation: S3 operation ('get_object' or 'put_object')

        Returns:
            Pre-signed URL

        Raises:
            Exception: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                operation,
                Params={
                    'Bucket': self.bucket,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            raise Exception(f"Failed to generate pre-signed URL: {e}")

    def generate_upload_url(
        self,
        filename: str,
        content_type: str = 'application/pdf',
        expiration: int = 3600
    ) -> dict:
        """
        Generate a pre-signed URL for direct upload from frontend.

        This allows the frontend to upload files directly to S3
        without going through the Lambda function.

        Args:
            filename: Original filename
            content_type: MIME type
            expiration: URL expiration time in seconds

        Returns:
            Dictionary with 'url' and 's3_key'
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f"pdfs/{timestamp}_{filename}"

        url = self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket,
                'Key': s3_key,
                'ContentType': content_type
            },
            ExpiresIn=expiration
        )

        return {
            'upload_url': url,
            's3_key': s3_key
        }

    def list_files(self, prefix: str = 'pdfs/', max_keys: int = 100) -> list:
        """
        List files in S3 bucket.

        Args:
            prefix: S3 key prefix to filter by
            max_keys: Maximum number of files to return

        Returns:
            List of file information dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                })

            return files

        except ClientError as e:
            print(f"Error listing files: {e}")
            return []

    def health_check(self) -> bool:
        """
        Check S3 bucket accessibility.

        Returns:
            True if bucket is accessible, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False


# Singleton instance
_s3_storage = None

def get_s3_storage() -> S3Storage:
    """
    Get or create S3Storage singleton.

    Returns:
        S3Storage instance
    """
    global _s3_storage
    if _s3_storage is None:
        _s3_storage = S3Storage()
    return _s3_storage
