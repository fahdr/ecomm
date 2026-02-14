"""
Image processing utilities for supplier product images.

For Developers:
    Provides async image downloading via httpx and synchronous image
    processing via Pillow. All processing methods accept raw bytes and
    return processed bytes, making them easy to compose in pipelines.

For QA Engineers:
    Image processing methods are stateless and operate on raw bytes.
    Use small test images (e.g. 10x10 pixel PNGs) to keep tests fast.
    The ``download_image()`` method requires network access or mocking.

For End Users:
    Automatically downloads, optimizes, and creates thumbnails of
    supplier product images for use in your storefront. Optimized
    images load faster and improve your store's performance.
"""

from __future__ import annotations

import io

import httpx
from PIL import Image

from ecomm_suppliers.base import SupplierError


class ImageService:
    """
    Service for downloading and processing supplier product images.

    For Developers:
        All methods are static. ``download_image()`` is async (uses httpx),
        while ``optimize_image()`` and ``create_thumbnail()`` are synchronous
        (CPU-bound Pillow operations). Run the sync methods in a thread pool
        if needed for high throughput.

    For QA Engineers:
        Use ``httpx``'s ``respx`` library to mock HTTP calls in
        ``download_image()`` tests. For processing tests, create minimal
        in-memory images with Pillow.
    """

    @staticmethod
    async def download_image(url: str, timeout: float = 30.0) -> bytes:
        """
        Download an image from a URL and return its raw bytes.

        For Developers:
            Uses httpx with a configurable timeout. Validates that the
            response content type is an image. Follows redirects.

        Args:
            url: Full URL of the image to download.
            timeout: Request timeout in seconds (default 30.0).

        Returns:
            Raw image bytes.

        Raises:
            SupplierError: If the download fails, times out, or returns
                a non-image content type.
        """
        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    raise SupplierError(
                        f"Image download failed with status {resp.status_code}: {url}",
                        status_code=resp.status_code,
                        supplier="image_service",
                    )
                content_type = resp.headers.get("content-type", "")
                if content_type and not content_type.startswith("image/"):
                    raise SupplierError(
                        f"Expected image content type, got '{content_type}': {url}",
                        supplier="image_service",
                    )
                return resp.content
        except httpx.HTTPError as exc:
            raise SupplierError(
                f"Image download failed: {exc}",
                supplier="image_service",
            ) from exc

    @staticmethod
    def optimize_image(
        data: bytes,
        max_width: int = 1200,
        quality: int = 85,
        output_format: str = "JPEG",
    ) -> bytes:
        """
        Optimize an image by resizing and compressing it.

        For Developers:
            Opens the image from bytes, resizes if wider than ``max_width``
            (preserving aspect ratio), converts to RGB (for JPEG compatibility),
            and compresses with the specified quality level.

        For End Users:
            Optimized images load faster on your storefront, improving
            page speed and customer experience.

        Args:
            data: Raw image bytes (any format Pillow supports).
            max_width: Maximum width in pixels. Images wider than this will
                be proportionally scaled down. Default 1200.
            quality: JPEG compression quality (1-100). Higher = better quality
                but larger file. Default 85.
            output_format: Output image format. Default "JPEG".

        Returns:
            Optimized image as bytes in the specified format.

        Raises:
            SupplierError: If the image data is invalid or processing fails.
        """
        try:
            img = Image.open(io.BytesIO(data))

            # Convert RGBA/P/LA to RGB for JPEG compatibility
            if img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if wider than max_width, preserving aspect ratio
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)

            # Compress and return bytes
            buffer = io.BytesIO()
            img.save(buffer, format=output_format, quality=quality, optimize=True)
            return buffer.getvalue()
        except SupplierError:
            raise
        except Exception as exc:
            raise SupplierError(
                f"Image optimization failed: {exc}",
                supplier="image_service",
            ) from exc

    @staticmethod
    def create_thumbnail(
        data: bytes,
        size: tuple[int, int] = (300, 300),
        output_format: str = "JPEG",
        quality: int = 85,
    ) -> bytes:
        """
        Create a thumbnail from an image.

        For Developers:
            Uses Pillow's ``thumbnail()`` method which preserves aspect ratio
            and fits the image within the specified bounding box. The original
            image is not upscaled if it's smaller than the thumbnail size.

        For End Users:
            Thumbnails are used in product listings, search results, and
            cart views for fast loading.

        Args:
            data: Raw image bytes (any format Pillow supports).
            size: Maximum (width, height) tuple for the thumbnail bounding box.
                Default (300, 300).
            output_format: Output image format. Default "JPEG".
            quality: Compression quality (1-100). Default 85.

        Returns:
            Thumbnail image as bytes in the specified format.

        Raises:
            SupplierError: If the image data is invalid or processing fails.
        """
        try:
            img = Image.open(io.BytesIO(data))

            # Convert to RGB for JPEG compatibility
            if img.mode in ("RGBA", "P", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if "A" in img.mode else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Create thumbnail (preserves aspect ratio, no upscaling)
            img.thumbnail(size, Image.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format=output_format, quality=quality, optimize=True)
            return buffer.getvalue()
        except SupplierError:
            raise
        except Exception as exc:
            raise SupplierError(
                f"Thumbnail creation failed: {exc}",
                supplier="image_service",
            ) from exc

    @staticmethod
    def get_image_dimensions(data: bytes) -> tuple[int, int]:
        """
        Get the width and height of an image from its raw bytes.

        Args:
            data: Raw image bytes.

        Returns:
            Tuple of (width, height) in pixels.

        Raises:
            SupplierError: If the image data is invalid.
        """
        try:
            img = Image.open(io.BytesIO(data))
            return img.size
        except Exception as exc:
            raise SupplierError(
                f"Failed to read image dimensions: {exc}",
                supplier="image_service",
            ) from exc

    @staticmethod
    def get_image_format(data: bytes) -> str | None:
        """
        Detect the format of an image from its raw bytes.

        Args:
            data: Raw image bytes.

        Returns:
            Image format string (e.g. "JPEG", "PNG", "WEBP") or None if
            the format cannot be determined.
        """
        try:
            img = Image.open(io.BytesIO(data))
            return img.format
        except Exception:
            return None
