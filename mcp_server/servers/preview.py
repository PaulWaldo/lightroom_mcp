"""
Preview server module for image generation
Priority implementation for AI visual feedback loop

Modality Overview
-----------------
This module provides two distinct categories of preview tools:

**MULTIMODAL tools (return image data)**
  preview_get_image_data  — Returns an MCP ImageContent block; vision-capable
                            clients (Claude Desktop, Continue, etc.) render the
                            image directly.  The response is NOT a file path.
  preview_get_image_data_as_text — Fallback for gateways/proxies that intercept
                            ImageContent blocks (e.g. Open WebUI). Returns the
                            same image as a base64 data URI inside a
                            TextContent block instead.

**TEXT/FILE tools (return file paths or metadata)**
  preview_generate            — Saves JPEG to disk, returns the file path as text
  preview_generate_current    — Same as above, always medium size
  preview_generate_comparison — Saves before/after JPEGs, returns both file paths
  preview_generate_batch      — Saves multiple JPEGs, returns paths + metadata
  preview_get_info            — Returns metadata / capability information (no image)

**ANALYSIS tools (return structured data)**
  histogram_analyze_current   — RGB + luminance histograms (no image in response)
  histogram_analyze_rgb       — RGB channel histograms (no image in response)
  histogram_analyze_luminance — Luminance histogram (no image in response)

Client Compatibility
--------------------
+-----------------------+--------------------+--------------------+
| Client                | ImageContent block | File-path tools    |
+-----------------------+--------------------+--------------------+
| Claude Desktop        | ✅ Renders inline  | ✅ Fully supported |
| Continue (VS Code)    | ✅ Renders inline  | ✅ Fully supported |
| Cursor                | ✅ Renders inline  | ✅ Fully supported |
| Other MCP clients     | ⚠️ Depends on impl | ✅ Fully supported |
+-----------------------+--------------------+--------------------+
Clients that do not support MCP ImageContent blocks will not render the
image inline.  Use preview_generate to save to disk instead.
"""

from typing import Dict, Any, Optional, List, Union
from mcp_server.shared.base import LightroomServerModule
from mcp_server.shared.resilient_client import resilient_client_manager
import base64
import logging
from pathlib import Path
import tempfile
import time
from PIL import Image
from fastmcp.utilities.types import Image as FastMCPImage
from mcp.types import TextContent
import io
import numpy as np

logger = logging.getLogger(__name__)


class PreviewServer(LightroomServerModule):
    """Preview generation tools for visual feedback"""

    @property
    def name(self) -> str:
        return "Lightroom Preview Tools"

    @property
    def prefix(self) -> str:
        return "preview"

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _fetch_preview_data(
        self, photo_id: str, size: str, quality: int
    ) -> tuple[str, dict]:
        """Fetch preview data from Lightroom, handling chunked or direct transfer.

        This is an internal transport helper that hides the socket-level chunking
        protocol used between Lightroom's Lua bridge and Python.  Callers receive
        a single complete base64 string regardless of how many chunks were needed.

        Args:
            photo_id: Lightroom photo ID
            size: Preview size ("small", "medium", "large", "full")
            quality: JPEG quality (1–100)

        Returns:
            Tuple of (base64_data, info_dict) where info_dict contains dimension
            and metadata fields returned by Lightroom.
        """
        params = {"photoId": photo_id, "size": size, "quality": quality, "base64": True}

        result = await self.execute_command("generatePreview", params)
        logger.debug(f"Generate preview result keys: {list(result.keys())}")

        if result.get("preview") == "CHUNKED_TRANSFER":
            # Reassemble socket-level chunks (internal transport detail)
            preview_id = result.get("previewId")
            chunk_size = result.get("chunkSize", 0)
            info = result.get("info", {})

            chunks = []
            chunk_index = 0

            while True:
                logger.debug(f"Downloading chunk {chunk_index}...")
                chunk_result = await self.execute_command(
                    "getPreviewChunk",
                    {
                        "previewId": preview_id,
                        "chunkIndex": chunk_index,
                        "chunkSize": chunk_size,
                    },
                )

                chunk_data = chunk_result.get("chunk", "")
                chunks.append(chunk_data)
                logger.debug(
                    f"Chunk {chunk_index}: {len(chunk_data)} chars, "
                    f"isLastChunk: {chunk_result.get('isLastChunk', False)}"
                )

                if chunk_result.get("isLastChunk", False):
                    logger.info(
                        f"Downloaded {chunk_index + 1} chunks, "
                        f"total size: {chunk_result.get('totalSize', 'unknown')} bytes"
                    )
                    break

                chunk_index += 1

            full_data = "".join(chunks)
            logger.info(f"Combined {len(chunks)} chunks into {len(full_data)} chars")
            return full_data, info

        else:
            # Direct (non-chunked) response
            info = result.get("info", {})
            preview_data = result.get("preview")
            if not preview_data:
                raise ValueError("No preview data returned from Lightroom")
            return preview_data, info

    def _process_preview_data(
        self, base64_data: str, size: str, quality: int
    ) -> tuple[bytes, int, int]:
        """Decode base64 preview data and resize/optimize to the requested size.

        Args:
            base64_data: Base64-encoded JPEG from Lightroom
            size: Target size ("small", "medium", "large", "full")
            quality: JPEG quality (1–100)

        Returns:
            Tuple of (jpeg_bytes, actual_width, actual_height)
        """
        jpeg_data = base64.b64decode(base64_data)

        if size != "full":
            jpeg_bytes, width, height = self._resize_and_optimize_jpeg(
                jpeg_data, size, quality
            )
        else:
            img = Image.open(io.BytesIO(jpeg_data))
            width, height = img.size
            # Re-compress at the requested quality even for "full"
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            jpeg_bytes = output.getvalue()

        return jpeg_bytes, width, height

    def _generate_preview_filename(
        self,
        photo_id: str,
        size: str,
        filename_hint: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Path:
        """Generate a path for preview storage.

        Args:
            photo_id: Photo ID
            size: Preview size
            filename_hint: Optional filename hint
            save_path: Optional directory or full file path.
                       - None: saves to the system temp directory (auto-cleanup)
                       - Directory path: saves there with an auto-generated name
                       - Full .jpg/.jpeg path: uses it directly
        """
        # Build the base filename
        if filename_hint:
            clean_hint = "".join(c for c in filename_hint if c.isalnum() or c in "._-")
            if size.lower() in clean_hint.lower():
                base_name = f"{clean_hint}.jpg"
            else:
                base_name = f"{clean_hint}_{size}.jpg"
        else:
            timestamp = int(time.time() * 1000)
            base_name = f"lr_preview_{photo_id}_{size}_{timestamp}.jpg"

        if save_path:
            path = Path(save_path)
            if path.suffix in [".jpg", ".jpeg"]:
                # Treat as a full file path
                path.parent.mkdir(parents=True, exist_ok=True)
                return path
            else:
                # Treat as a directory
                path.mkdir(parents=True, exist_ok=True)
                return path / base_name
        else:
            # Default: system temp directory (auto-cleaned by the OS)
            return Path(tempfile.gettempdir()) / base_name

    def _resize_and_optimize_jpeg(
        self, jpeg_data: bytes, size: str, quality: int
    ) -> tuple[bytes, int, int]:
        """Resize and optimize JPEG data based on size parameter.

        Returns: (optimized_jpeg_data, actual_width, actual_height)
        """
        size_targets = {"small": 640, "medium": 1080, "large": 1440, "full": None}

        target_size = size_targets.get(size)
        if target_size is None:
            img = Image.open(io.BytesIO(jpeg_data))
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            return output.getvalue(), img.width, img.height

        img = Image.open(io.BytesIO(jpeg_data))
        orig_width, orig_height = img.size

        if orig_width > orig_height:
            new_width = target_size
            new_height = int(target_size * orig_height / orig_width)
        else:
            new_height = target_size
            new_width = int(target_size * orig_width / orig_height)

        if orig_width > new_width or orig_height > new_height:
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            new_width, new_height = orig_width, orig_height

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)

        return output.getvalue(), new_width, new_height

    def _analyze_histogram_from_base64(
        self, base64_data: str, channels: str = "all"
    ) -> Dict[str, Any]:
        """Analyze histogram from base64 image data.

        Args:
            base64_data: Base64 encoded JPEG data
            channels: "all", "rgb", or "luminance"

        Returns:
            Dictionary with histogram data and statistics
        """
        try:
            jpeg_data = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(jpeg_data))

            if img.mode != "RGB":
                img = img.convert("RGB")

            img_array = np.array(img)
            height, width, channels_count = img_array.shape

            result = {
                "success": True,
                "image_dimensions": f"{width}x{height}",
                "total_pixels": width * height,
            }

            if channels in ["all", "rgb"]:
                red_channel = img_array[:, :, 0].flatten()
                green_channel = img_array[:, :, 1].flatten()
                blue_channel = img_array[:, :, 2].flatten()

                red_hist, _ = np.histogram(red_channel, bins=256, range=(0, 256))
                green_hist, _ = np.histogram(green_channel, bins=256, range=(0, 256))
                blue_hist, _ = np.histogram(blue_channel, bins=256, range=(0, 256))

                result["rgb"] = {
                    "histograms": {
                        "red": red_hist.tolist(),
                        "green": green_hist.tolist(),
                        "blue": blue_hist.tolist(),
                    },
                    "statistics": {
                        "red": {
                            "mean": float(np.mean(red_channel)),
                            "median": float(np.median(red_channel)),
                            "std": float(np.std(red_channel)),
                            "min": int(np.min(red_channel)),
                            "max": int(np.max(red_channel)),
                        },
                        "green": {
                            "mean": float(np.mean(green_channel)),
                            "median": float(np.median(green_channel)),
                            "std": float(np.std(green_channel)),
                            "min": int(np.min(green_channel)),
                            "max": int(np.max(green_channel)),
                        },
                        "blue": {
                            "mean": float(np.mean(blue_channel)),
                            "median": float(np.median(blue_channel)),
                            "std": float(np.std(blue_channel)),
                            "min": int(np.min(blue_channel)),
                            "max": int(np.max(blue_channel)),
                        },
                    },
                }

                total_pixels = width * height
                result["rgb"]["clipping"] = {
                    "shadows_clipped": {
                        "red": int(np.sum(red_channel == 0)),
                        "green": int(np.sum(green_channel == 0)),
                        "blue": int(np.sum(blue_channel == 0)),
                    },
                    "highlights_clipped": {
                        "red": int(np.sum(red_channel == 255)),
                        "green": int(np.sum(green_channel == 255)),
                        "blue": int(np.sum(blue_channel == 255)),
                    },
                    "shadow_clipping_percent": {
                        "red": float(np.sum(red_channel == 0) / total_pixels * 100),
                        "green": float(np.sum(green_channel == 0) / total_pixels * 100),
                        "blue": float(np.sum(blue_channel == 0) / total_pixels * 100),
                    },
                    "highlight_clipping_percent": {
                        "red": float(np.sum(red_channel == 255) / total_pixels * 100),
                        "green": float(
                            np.sum(green_channel == 255) / total_pixels * 100
                        ),
                        "blue": float(np.sum(blue_channel == 255) / total_pixels * 100),
                    },
                }

            if channels in ["all", "luminance"]:
                luminance = (
                    (
                        0.299 * img_array[:, :, 0]
                        + 0.587 * img_array[:, :, 1]
                        + 0.114 * img_array[:, :, 2]
                    )
                    .flatten()
                    .astype(np.uint8)
                )

                luminance_hist, _ = np.histogram(luminance, bins=256, range=(0, 256))

                result["luminance"] = {
                    "histogram": luminance_hist.tolist(),
                    "statistics": {
                        "mean": float(np.mean(luminance)),
                        "median": float(np.median(luminance)),
                        "std": float(np.std(luminance)),
                        "min": int(np.min(luminance)),
                        "max": int(np.max(luminance)),
                    },
                    "clipping": {
                        "shadows_clipped": int(np.sum(luminance == 0)),
                        "highlights_clipped": int(np.sum(luminance == 255)),
                        "shadow_clipping_percent": float(
                            np.sum(luminance == 0) / len(luminance) * 100
                        ),
                        "highlight_clipping_percent": float(
                            np.sum(luminance == 255) / len(luminance) * 100
                        ),
                    },
                    "tonal_distribution": {
                        "shadows_percent": float(
                            np.sum(luminance < 85) / len(luminance) * 100
                        ),
                        "midtones_percent": float(
                            np.sum((luminance >= 85) & (luminance < 170))
                            / len(luminance)
                            * 100
                        ),
                        "highlights_percent": float(
                            np.sum(luminance >= 170) / len(luminance) * 100
                        ),
                    },
                }

            return result

        except Exception as e:
            logger.error(f"Histogram analysis failed: {e}")
            return {"success": False, "error": f"Failed to analyze histogram: {str(e)}"}

    def _save_preview_to_disk(
        self, jpeg_bytes: bytes, file_path: Path, actual_width: int, actual_height: int
    ) -> Dict[str, Any]:
        """Write processed JPEG bytes to disk and return metadata.

        Args:
            jpeg_bytes: Ready-to-write JPEG bytes (already resized/optimized)
            file_path: Destination path
            actual_width: Width of the processed image
            actual_height: Height of the processed image

        Returns:
            Dictionary with success status and file metadata
        """
        try:
            with open(file_path, "wb") as f:
                f.write(jpeg_bytes)

            file_stats = file_path.stat()

            return {
                "success": True,
                "file_path": str(file_path),
                "file_size_bytes": file_stats.st_size,
                "file_size_mb": round(file_stats.st_size / (1024 * 1024), 2),
                "actual_width": actual_width,
                "actual_height": actual_height,
            }
        except Exception as e:
            logger.error(f"Failed to save preview to disk: {e}")
            return {"success": False, "error": f"Failed to save preview: {str(e)}"}

    # -------------------------------------------------------------------------
    # MCP tools
    # -------------------------------------------------------------------------

    def _setup_tools(self):
        """Register preview tools"""

        @self.server.tool
        async def preview_generate(
            photo_id: Optional[str] = None,
            size: str = "medium",
            quality: Optional[int] = None,
            filename: Optional[str] = None,
            save_path: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Save a JPEG preview to disk and return its file path (TEXT/FILE
            output — no image data in the response). To visually inspect the
            photo yourself, use preview_get_image_data instead.

            By default, saves to the system temp directory (auto-cleaned).

            Args:
                photo_id: Photo ID (uses current selection if not provided)
                size: "small" (640px longest edge), "medium" (1080px),
                      "large" (1440px), or "full" (original resolution)
                quality: Optional JPEG quality override (1-100)
                filename: Optional filename hint for the saved file
                save_path: None=temp dir (default), a directory, or a full
                           .jpg file path

            Returns:
                Dictionary with file_path and metadata
            """
            if not photo_id:
                try:
                    selected = await self.execute_command(
                        "catalog.getSelectedPhotos", {}
                    )
                    if selected.get("count", 0) == 0:
                        return {
                            "success": False,
                            "error": "No photo selected in Lightroom",
                            "hint": "Please select a photo or provide photo_id parameter",
                        }
                    photo_id = str(selected["photos"][0]["id"])
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to get selected photo: {e}",
                    }

            if quality is None:
                quality_defaults = {"small": 50, "medium": 90, "large": 90, "full": 90}
                quality = quality_defaults.get(size, 90)

            try:
                full_data, info = await self._fetch_preview_data(
                    photo_id, size, quality
                )
                jpeg_bytes, actual_width, actual_height = self._process_preview_data(
                    full_data, size, quality
                )

                file_path = self._generate_preview_filename(
                    photo_id, size, filename, save_path
                )
                save_result = self._save_preview_to_disk(
                    jpeg_bytes, file_path, actual_width, actual_height
                )

                if save_result["success"]:
                    response = {
                        "success": True,
                        "file_path": save_result["file_path"],
                        "photo_id": info.get("photoId", photo_id),
                        "size": size,
                        "actual_width": actual_width,
                        "actual_height": actual_height,
                        "original_width": info.get("width"),
                        "original_height": info.get("height"),
                        "lightroom_requested": f"{info.get('requestedWidth', 'unknown')}x{info.get('requestedHeight', 'unknown')}",
                        "file_size_bytes": save_result["file_size_bytes"],
                        "file_size_mb": save_result["file_size_mb"],
                        "quality": quality,
                    }
                    logger.info(f"Preview saved to: {save_result['file_path']}")
                    return response
                else:
                    return save_result

            except Exception as e:
                logger.error(f"Preview generation failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }

        @self.server.tool
        async def preview_get_image_data(
            photo_id: Optional[str] = None,
            size: str = "medium",
            quality: Optional[int] = None,
        ) -> Union[FastMCPImage, Dict[str, Any]]:
            """
            Generate a JPEG preview and return it inline as an MCP
            ImageContent block. RECOMMENDED tool for visually inspecting a
            photo — no filesystem access needed.

            GATEWAY WARNING: some gateways/proxies (e.g. Open WebUI)
            intercept ImageContent blocks and replace them with a JSON stub
            containing "fileName"/"markdown"/"$hint" instead of a "data"
            field. If you see that, you did NOT receive the image — try
            preview_get_image_data_as_text as a fallback, or use
            preview_generate (saves to disk) instead.

            Args:
                photo_id: Photo ID (uses current selection if not provided)
                size: "small" (640px longest edge, ~30-80KB), "medium"
                      (1080px, ~200-500KB, default), "large" (1440px), or
                      "full" (original resolution)
                quality: Optional JPEG quality override (1-100)

            Returns:
                MCP ImageContent block, or a JSON error dict on failure.
            """
            if not photo_id:
                try:
                    selected = await self.execute_command(
                        "catalog.getSelectedPhotos", {}
                    )
                    if selected.get("count", 0) == 0:
                        return {
                            "success": False,
                            "error": "No photo selected in Lightroom",
                            "hint": "Please select a photo or provide photo_id parameter",
                        }
                    photo_id = str(selected["photos"][0]["id"])
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to get selected photo: {e}",
                    }

            if quality is None:
                quality_defaults = {"small": 50, "medium": 90, "large": 90, "full": 90}
                quality = quality_defaults.get(size, 90)

            try:
                full_data, info = await self._fetch_preview_data(
                    photo_id, size, quality
                )
                jpeg_bytes, actual_width, actual_height = self._process_preview_data(
                    full_data, size, quality
                )

                logger.info(
                    f"Returning image data inline: photo={info.get('photoId', photo_id)}, "
                    f"{actual_width}x{actual_height}, {len(jpeg_bytes)} bytes, quality={quality}"
                )

                # Return a proper MCP ImageContent block so vision-capable LLMs
                # (Claude, GPT-4o, etc.) receive the image through the correct
                # content channel rather than as a text/JSON blob.
                return FastMCPImage(data=jpeg_bytes, format="jpeg")

            except Exception as e:
                logger.error(f"Preview image data generation failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }

        @self.server.tool
        async def preview_get_image_data_as_text(
            photo_id: Optional[str] = None,
            size: str = "small",
            quality: Optional[int] = None,
        ) -> Union[TextContent, Dict[str, Any]]:
            """
            Fallback for preview_get_image_data: returns the JPEG as a
            "data:image/jpeg;base64,..." URI in a TextContent block instead
            of an ImageContent block. Produces a much larger response, so
            prefer size="small" and low quality.

            Args:
                photo_id: Photo ID (uses current selection if not provided)
                size: "small" (640px longest edge, default), "medium"
                      (1080px), "large" (1440px), or "full"
                quality: Optional JPEG quality override (1-100)

            Returns:
                MCP TextContent block with a base64 data URI, or a JSON
                error dict on failure.
            """
            if not photo_id:
                try:
                    selected = await self.execute_command(
                        "catalog.getSelectedPhotos", {}
                    )
                    if selected.get("count", 0) == 0:
                        return {
                            "success": False,
                            "error": "No photo selected in Lightroom",
                            "hint": "Please select a photo or provide photo_id parameter",
                        }
                    photo_id = str(selected["photos"][0]["id"])
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to get selected photo: {e}",
                    }

            if quality is None:
                quality_defaults = {"small": 50, "medium": 90, "large": 90, "full": 90}
                quality = quality_defaults.get(size, 90)

            try:
                full_data, info = await self._fetch_preview_data(
                    photo_id, size, quality
                )
                jpeg_bytes, actual_width, actual_height = self._process_preview_data(
                    full_data, size, quality
                )

                b64_data = base64.b64encode(jpeg_bytes).decode("ascii")
                data_uri = f"data:image/jpeg;base64,{b64_data}"

                logger.info(
                    f"Returning image data as text/data-URI: photo={info.get('photoId', photo_id)}, "
                    f"{actual_width}x{actual_height}, {len(jpeg_bytes)} bytes, "
                    f"{len(data_uri)} chars, quality={quality}"
                )

                # Send through the TEXT content channel rather than ImageContent
                # so gateways that only intercept/transform ImageContent blocks
                # pass this through unmodified.
                return TextContent(type="text", text=data_uri)

            except Exception as e:
                logger.error(f"Preview image data (text) generation failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }

        @self.server.tool
        async def preview_generate_current(
            filename: Optional[str] = None, save_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Save a preview of the currently selected photo to disk (file path
            only, no image data). Always medium size (1080px), quality 90.
            For inline image data instead, use preview_get_image_data.

            Args:
                filename: Optional filename hint for the saved file
                save_path: None=temp dir (default), a directory, or a full
                           .jpg file path

            Returns:
                Dictionary with file_path and metadata
            """
            try:
                selected = await self.execute_command("catalog.getSelectedPhotos", {})
                if selected.get("count", 0) == 0:
                    return {"success": False, "error": "No photo selected in Lightroom"}

                photo_id = str(selected["photos"][0]["id"])

                full_data, info = await self._fetch_preview_data(photo_id, "medium", 90)
                jpeg_bytes, actual_width, actual_height = self._process_preview_data(
                    full_data, "medium", 90
                )

                file_path = self._generate_preview_filename(
                    photo_id, "medium", filename, save_path
                )
                save_result = self._save_preview_to_disk(
                    jpeg_bytes, file_path, actual_width, actual_height
                )

                if save_result["success"]:
                    return {
                        "success": True,
                        "file_path": save_result["file_path"],
                        "photo_id": info.get("photoId", photo_id),
                        "size": "medium",
                        "actual_width": actual_width,
                        "actual_height": actual_height,
                        "file_size_bytes": save_result["file_size_bytes"],
                        "file_size_mb": save_result["file_size_mb"],
                        "quality": 90,
                    }
                else:
                    return save_result

            except Exception as e:
                logger.error(f"Current preview generation failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }

        @self.server.tool
        async def preview_get_info(photo_id: Optional[str] = None) -> Dict[str, Any]:
            """
            Get information about preview generation for a photo.

            Args:
                photo_id: Photo ID (uses current selection if not provided)

            Returns:
                Preview generation information
            """
            if not photo_id:
                try:
                    selected = await self.execute_command(
                        "catalog.getSelectedPhotos", {}
                    )
                    if selected.get("count", 0) == 0:
                        return {
                            "success": False,
                            "error": "No photo selected in Lightroom",
                        }
                    photo_id = str(selected["photos"][0]["id"])
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to get selected photo: {e}",
                    }

            try:
                result = await self.execute_command(
                    "getPreviewInfo", {"photoId": photo_id}
                )

                return {
                    "success": True,
                    "photo_id": photo_id,
                    "available_sizes": {
                        "small": "640px longest edge, quality 50",
                        "medium": "1080px longest edge, quality 90",
                        "large": "1440px longest edge, quality 90",
                        "full": "original resolution, quality 90",
                    },
                    "max_quality": 100,
                    "note": (
                        "Use preview_get_image_data to get image data inline (no filesystem needed). "
                        "Use preview_generate to save a file to the system temp directory."
                    ),
                    "lightroom_info": result,
                }

            except Exception as e:
                logger.error(f"Preview info failed: {e}")
                return {
                    "success": True,
                    "photo_id": photo_id,
                    "available_sizes": {
                        "small": "640px longest edge, quality 50",
                        "medium": "1080px longest edge, quality 90",
                        "large": "1440px longest edge, quality 90",
                        "full": "original resolution, quality 90",
                    },
                    "max_quality": 100,
                    "note": (
                        "Use preview_get_image_data to get image data inline (no filesystem needed). "
                        "Use preview_generate to save a file to the system temp directory."
                    ),
                    "lightroom_info": "Default info (Lightroom command unavailable)",
                }

        @self.server.tool
        async def preview_generate_comparison(
            before_settings: Optional[Dict[str, float]] = None,
            after_settings: Optional[Dict[str, float]] = None,
            size: str = "medium",
            quality: Optional[int] = None,
            save_path: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Save before/after comparison previews to disk (file paths only,
            no image data). Useful for evaluating the impact of adjustments.

            Args:
                before_settings: Develop settings for "before" (None = current)
                after_settings: Develop settings for "after"
                size: Preview size (small, medium, large, full)
                quality: Optional JPEG quality override (1-100)
                save_path: Optional save location directory

            Returns:
                File paths and metadata for both previews
            """
            try:
                selected = await self.execute_command("catalog.getSelectedPhotos", {})
                if selected.get("count", 0) == 0:
                    return {"success": False, "error": "No photo selected"}

                photo_id = str(selected["photos"][0]["id"])

                if quality is None:
                    quality_defaults = {
                        "small": 50,
                        "medium": 90,
                        "large": 90,
                        "full": 90,
                    }
                    quality = quality_defaults.get(size, 90)

                original_settings = await self.execute_command(
                    "develop.getSettings", {"photoId": photo_id}
                )

                if before_settings:
                    await self.execute_command(
                        "develop.applySettings",
                        {"photoId": photo_id, "settings": before_settings},
                    )

                # Generate before preview
                before_data, before_info = await self._fetch_preview_data(
                    photo_id, size, quality
                )
                before_jpeg, before_w, before_h = self._process_preview_data(
                    before_data, size, quality
                )

                before_file_path = self._generate_preview_filename(
                    photo_id, size, "before", save_path
                )
                before_save_result = self._save_preview_to_disk(
                    before_jpeg, before_file_path, before_w, before_h
                )

                if not before_save_result["success"]:
                    return before_save_result

                if after_settings:
                    await self.execute_command(
                        "develop.applySettings",
                        {"photoId": photo_id, "settings": after_settings},
                    )

                # Generate after preview
                after_data, after_info = await self._fetch_preview_data(
                    photo_id, size, quality
                )
                after_jpeg, after_w, after_h = self._process_preview_data(
                    after_data, size, quality
                )

                after_file_path = self._generate_preview_filename(
                    photo_id, size, "after", save_path
                )
                after_save_result = self._save_preview_to_disk(
                    after_jpeg, after_file_path, after_w, after_h
                )

                if not after_save_result["success"]:
                    return after_save_result

                await self.execute_command(
                    "develop.applySettings",
                    {"photoId": photo_id, "settings": original_settings["settings"]},
                )

                return {
                    "success": True,
                    "photo_id": photo_id,
                    "before": {
                        "file_path": before_save_result["file_path"],
                        "actual_width": before_w,
                        "actual_height": before_h,
                        "file_size_bytes": before_save_result["file_size_bytes"],
                        "file_size_mb": before_save_result["file_size_mb"],
                    },
                    "after": {
                        "file_path": after_save_result["file_path"],
                        "actual_width": after_w,
                        "actual_height": after_h,
                        "file_size_bytes": after_save_result["file_size_bytes"],
                        "file_size_mb": after_save_result["file_size_mb"],
                    },
                    "size": size,
                    "quality": quality,
                }

            except Exception as e:
                logger.error(f"Comparison generation failed: {e}")
                return {"success": False, "error": str(e)}

        @self.server.tool
        async def preview_generate_batch(
            photo_ids: List[str], size: str = "small", quality: int = 85
        ) -> Dict[str, Any]:
            """
            Save previews for multiple photos to disk (file paths only, no
            image data). Efficient batch generation for browsing/selection.

            Args:
                photo_ids: List of photo IDs
                size: Preview size (recommend "small" for batches)
                quality: JPEG quality

            Returns:
                Dictionary of previews by photo ID
            """
            result = await self.execute_command(
                "generateBatchPreviews",
                {"photoIds": photo_ids, "size": size, "quality": quality},
            )

            return {
                "success": True,
                "count": result.get("successful", 0),
                "previews": result.get("results", []),
            }

        @self.server.tool
        async def histogram_analyze_current() -> Dict[str, Any]:
            """
            Analyze RGB and luminance histograms of the currently selected photo.

            Generates a small preview (640px) optimized for histogram analysis,
            then calculates histograms, statistics, and clipping analysis for
            RGB channels and luminance.

            Returns:
                Dictionary with histogram data, statistics, and analysis
            """
            try:
                selected = await self.execute_command("catalog.getSelectedPhotos", {})
                if selected.get("count", 0) == 0:
                    return {
                        "success": False,
                        "error": "No photo selected in Lightroom",
                        "hint": "Please select a photo and try again",
                    }

                photo_id = str(selected["photos"][0]["id"])

                full_data, info = await self._fetch_preview_data(photo_id, "small", 30)

                histogram_result = self._analyze_histogram_from_base64(full_data, "all")

                if histogram_result.get("success"):
                    histogram_result.update(
                        {
                            "photo_id": photo_id,
                            "preview_size": "small (640px longest edge)",
                            "preview_quality": 30,
                            "analysis_type": "RGB + Luminance",
                        }
                    )

                return histogram_result

            except Exception as e:
                logger.error(f"Histogram analysis failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }

        @self.server.tool
        async def histogram_analyze_rgb() -> Dict[str, Any]:
            """
            Analyze RGB channel histograms of the currently selected photo.

            Generates a small preview optimized for analysis, then calculates
            histograms, statistics, and clipping analysis for Red, Green,
            and Blue channels only.

            Returns:
                Dictionary with RGB histogram data and statistics
            """
            try:
                selected = await self.execute_command("catalog.getSelectedPhotos", {})
                if selected.get("count", 0) == 0:
                    return {
                        "success": False,
                        "error": "No photo selected in Lightroom",
                        "hint": "Please select a photo and try again",
                    }

                photo_id = str(selected["photos"][0]["id"])

                full_data, _ = await self._fetch_preview_data(photo_id, "small", 30)

                histogram_result = self._analyze_histogram_from_base64(full_data, "rgb")

                if histogram_result.get("success"):
                    histogram_result.update(
                        {
                            "photo_id": photo_id,
                            "preview_size": "small (640px longest edge)",
                            "preview_quality": 30,
                            "analysis_type": "RGB channels only",
                        }
                    )

                return histogram_result

            except Exception as e:
                logger.error(f"RGB histogram analysis failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }

        @self.server.tool
        async def histogram_analyze_luminance() -> Dict[str, Any]:
            """
            Analyze luminance histogram of the currently selected photo.

            Generates a small preview optimized for analysis, then calculates
            luminance histogram, statistics, clipping analysis, and tonal
            distribution (shadows/midtones/highlights).

            Returns:
                Dictionary with luminance histogram data and tonal analysis
            """
            try:
                selected = await self.execute_command("catalog.getSelectedPhotos", {})
                if selected.get("count", 0) == 0:
                    return {
                        "success": False,
                        "error": "No photo selected in Lightroom",
                        "hint": "Please select a photo and try again",
                    }

                photo_id = str(selected["photos"][0]["id"])

                full_data, _ = await self._fetch_preview_data(photo_id, "small", 30)

                histogram_result = self._analyze_histogram_from_base64(
                    full_data, "luminance"
                )

                if histogram_result.get("success"):
                    histogram_result.update(
                        {
                            "photo_id": photo_id,
                            "preview_size": "small (640px longest edge)",
                            "preview_quality": 30,
                            "analysis_type": "Luminance only",
                        }
                    )

                return histogram_result

            except Exception as e:
                logger.error(f"Luminance histogram analysis failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "hint": "Ensure a photo is selected in Lightroom",
                }


# Create server instance
preview_server = PreviewServer()
