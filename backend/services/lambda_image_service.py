"""
Service to invoke the image processor Lambda function.
Used by main Lambda to extract images from design-heavy PDFs.
"""

import json
import base64
import os
from typing import List, Optional
from config import Config


class LambdaImageService:
    """Service for invoking the image processor Lambda function."""

    def __init__(self):
        self.lambda_function_name = os.environ.get(
            "IMAGE_PROCESSOR_LAMBDA_ARN", "knowledge-base-image-processor"
        )
        self.is_lambda = Config.IS_LAMBDA

        # Only import boto3 in Lambda environment
        if self.is_lambda:
            import boto3

            self.lambda_client = boto3.client("lambda")
        else:
            self.lambda_client = None

    def extract_images_from_pdf(
        self, file_bytes: bytes, page_numbers: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Extract images from PDF using the image processor Lambda.

        Args:
            file_bytes: PDF file content as bytes
            page_numbers: Optional list of page numbers (0-indexed)

        Returns:
            List of image dicts with id, type, box, page, and image_b64
        """
        if not self.is_lambda:
            # In local dev, fall back to local extraction
            print("[WARN] Not in Lambda - using local image extraction fallback")
            return self._local_fallback(file_bytes, page_numbers)

        try:
            # Prepare payload for image processor Lambda
            payload = {
                "operation": "extract_images",
                "file_bytes_base64": base64.b64encode(file_bytes).decode("utf-8"),
            }

            if page_numbers is not None:
                payload["page_numbers"] = page_numbers

            print(
                f"[INFO] Invoking image processor Lambda: {self.lambda_function_name}"
            )

            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_name,
                InvocationType="RequestResponse",  # Synchronous
                Payload=json.dumps(payload),
            )

            # Parse response
            response_payload = json.loads(response["Payload"].read())

            if response_payload.get("statusCode") != 200:
                error_msg = response_payload.get("body", {}).get(
                    "error", "Unknown error"
                )
                print(f"[ERROR] Image processor Lambda failed: {error_msg}")
                return []

            body = json.loads(response_payload.get("body", "{}"))
            images = body.get("images", [])

            print(f"[INFO] Received {len(images)} images from Lambda")
            return images

        except Exception as e:
            print(f"[ERROR] Failed to invoke image processor Lambda: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _local_fallback(
        self, file_bytes: bytes, page_numbers: Optional[List[int]] = None
    ) -> List[dict]:
        """
        Fallback for local development - use pdfplumber instead of PyMuPDF.
        Returns basic image metadata without base64 data.
        """
        try:
            import pdfplumber
            import io

            images = []

            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages_to_process = (
                    page_numbers if page_numbers else range(len(pdf.pages))
                )

                for page_num in pages_to_process:
                    if page_num >= len(pdf.pages):
                        continue

                    page = pdf.pages[page_num]

                    for img_index, img in enumerate(page.images):
                        images.append(
                            {
                                "id": f"p{page_num+1}-img-{img_index}",
                                "type": "image",
                                "subtype": "embedded",
                                "box": {
                                    "l": img["x0"],
                                    "t": img["top"],
                                    "r": img["x1"],
                                    "b": img["bottom"],
                                },
                                "page": page_num + 1,
                                "image_b64": None,  # Not extracted in local mode
                            }
                        )

            print(f"[INFO] Local fallback extracted {len(images)} image placeholders")
            return images

        except Exception as e:
            print(f"[ERROR] Local fallback failed: {e}")
            return []


# Singleton instance
_lambda_image_service = None


def get_lambda_image_service() -> LambdaImageService:
    """Get or create the Lambda image service singleton."""
    global _lambda_image_service
    if _lambda_image_service is None:
        _lambda_image_service = LambdaImageService()
    return _lambda_image_service
