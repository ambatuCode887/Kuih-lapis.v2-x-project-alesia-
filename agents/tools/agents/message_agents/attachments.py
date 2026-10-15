from __future__ import annotations

import asyncio
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from PIL import Image, ImageOps
from pypdf import PdfReader

_ARTIFACT_MARKER = re.compile(r'\[Uploaded Artifact:\s*"([^"]+)"\]')
_MAX_FILE_BYTES = 20 * 1024 * 1024
_MAX_PDF_PAGES = 20
_MAX_IMAGE_PIXELS = 40_000_000
_MAX_OUTPUT_CHARACTERS = 30_000
_OCR_TIMEOUT_SECONDS = 45


def has_attachment(content: types.Content | None) -> bool:
    if not content:
        return False
    for part in content.parts or []:
        if getattr(part, "inline_data", None) or getattr(part, "file_data", None):
            return True
        if getattr(part, "text", None) and _ARTIFACT_MARKER.search(part.text):
            return True
    return False


def redact_historical_attachments(session, current_invocation_id: str) -> None:
    for event in getattr(session, "events", ()):
        if (
            event.invocation_id == current_invocation_id
            or event.content is None
        ):
            continue
        parts = event.content.parts or []
        has_attachment_data = any(
            getattr(part, "inline_data", None)
            or getattr(part, "file_data", None)
            or (
                getattr(part, "text", None)
                and (
                    "[BEGIN UNTRUSTED ATTACHMENT DATA" in part.text
                    or "[Extracted attachment text;" in part.text
                )
            )
            for part in parts
        )
        if not has_attachment_data:
            continue
        event.content.parts = [
            part
            for part in parts
            if not (
                getattr(part, "inline_data", None)
                or getattr(part, "file_data", None)
                or (
                    getattr(part, "text", None)
                    and (
                        "[BEGIN UNTRUSTED ATTACHMENT DATA" in part.text
                        or "[Extracted attachment text;" in part.text
                    )
                )
            )
        ] + [types.Part(text="[Prior attachment omitted from model history.]")]


def isolate_current_turn(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> None:
    def is_user_turn(content: types.Content) -> bool:
        parts = content.parts or []
        if content.role != "user" or not parts:
            return False
        # ADK presents other agents' output as user-role "For context:" messages.
        if (parts[0].text or "").startswith("For context:"):
            return False
        return any(
            getattr(part, "text", None) is not None
            or getattr(part, "inline_data", None) is not None
            or getattr(part, "file_data", None) is not None
            for part in parts
        )

    latest_user_index = next(
        (
            index
            for index in range(len(llm_request.contents) - 1, -1, -1)
            if is_user_turn(llm_request.contents[index])
        ),
        None,
    )
    if latest_user_index is None:
        return
    if latest_user_index:
        del llm_request.contents[:latest_user_index]
    latest_user_content = llm_request.contents[0]

    for content in llm_request.contents:
        is_latest_user_content = content is latest_user_content
        retained_parts = []
        removed_attachment = False
        for part in content.parts or []:
            is_binary_attachment = bool(
                getattr(part, "inline_data", None)
                or getattr(part, "file_data", None)
            )
            text = getattr(part, "text", None)
            is_historical_attachment_text = bool(
                text
                and not is_latest_user_content
                and (
                    "[BEGIN UNTRUSTED ATTACHMENT DATA" in text
                    or "[Extracted attachment text;" in text
                )
            )
            if is_binary_attachment or is_historical_attachment_text:
                removed_attachment = True
                continue
            retained_parts.append(part)
        if removed_attachment:
            retained_parts.append(
                types.Part(text="[Prior attachment omitted from model history.]")
            )
        content.parts = retained_parts


def _ocr_image(image: Image.Image) -> str:
    binary = shutil.which(os.getenv("TESSERACT_CMD", "tesseract"))
    if binary is None:
        raise RuntimeError(
            "Tesseract OCR was not found. Install it or set TESSERACT_CMD."
        )
    if image.width * image.height > _MAX_IMAGE_PIXELS:
        raise ValueError("Image dimensions exceed the supported limit.")

    normalized = ImageOps.exif_transpose(image).convert("RGB")
    with tempfile.TemporaryDirectory() as directory:
        image_path = Path(directory) / "attachment.png"
        normalized.save(image_path, format="PNG")
        result = subprocess.run(
            [binary, str(image_path), "stdout"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_OCR_TIMEOUT_SECONDS,
            check=False,
        )
    if result.returncode:
        raise RuntimeError("Tesseract could not read the image.")
    return result.stdout.strip()


def _ocr_pdf(data: bytes, page_indexes: list[int]) -> dict[int, str]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(data)
    pages = {}
    for page_index in page_indexes:
        page = document[page_index]
        bitmap = page.render(scale=1.5)
        image = bitmap.to_pil()
        text = _ocr_image(image)
        if text:
            pages[page_index] = text
        bitmap.close()
        page.close()
    document.close()
    return pages


def _extract_attachment(name: str, mime_type: str, data: bytes) -> str:
    if len(data) > _MAX_FILE_BYTES:
        raise ValueError("Files larger than 20 MB are not supported.")

    suffix = Path(name).suffix.casefold()
    normalized_mime = (mime_type or "").casefold()
    if normalized_mime == "application/pdf" or suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data), strict=False)
        page_count = min(len(reader.pages), _MAX_PDF_PAGES)
        pages_by_index = {}
        pages_needing_ocr = []
        for index in range(page_count):
            text = (reader.pages[index].extract_text() or "").strip()
            if text:
                pages_by_index[index] = text
            else:
                pages_needing_ocr.append(index)
        if pages_needing_ocr:
            pages_by_index.update(_ocr_pdf(data, pages_needing_ocr))
        extracted = "\n\n".join(
            f"[Page {index + 1}]\n{pages_by_index[index]}"
            for index in range(page_count)
            if pages_by_index.get(index)
        )
        if len(reader.pages) > _MAX_PDF_PAGES:
            extracted += f"\n\nOnly the first {_MAX_PDF_PAGES} pages were processed."
        return extracted[:_MAX_OUTPUT_CHARACTERS]

    if normalized_mime.startswith("image/") or suffix in {
        ".bmp",
        ".gif",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }:
        with Image.open(io.BytesIO(data)) as image:
            return _ocr_image(image)[:_MAX_OUTPUT_CHARACTERS]

    raise ValueError("Only PDF and image attachments are supported.")


async def _load_artifact(ctx: InvocationContext, filename: str) -> types.Part | None:
    if ctx.artifact_service is None:
        return None
    return await ctx.artifact_service.load_artifact(
        app_name=ctx.app_name,
        user_id=ctx.user_id,
        session_id=ctx.session.id,
        filename=filename,
    )


async def prepare_message_attachments(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> None:
    user_content = next(
        (content for content in reversed(llm_request.contents) if content.role == "user"),
        None,
    )
    if user_content is not None and has_attachment(user_content):
        invocation_context = callback_context.get_invocation_context()
        prepared_content = await preprocess_message_content(
            user_content,
            invocation_context,
        )
        user_content.parts = prepared_content.parts
    isolate_current_turn(callback_context, llm_request)


async def preprocess_message_content(
    user_content: types.Content | None,
    invocation_context: InvocationContext,
) -> types.Content | None:
    """Replace attachment binaries with untrusted extracted text for all agents."""
    if user_content is None or not has_attachment(user_content):
        return user_content

    retained_parts = []
    reports = []
    artifact_names = []
    consumed_names = set()

    for part in user_content.parts or []:
        inline_data = getattr(part, "inline_data", None)
        if inline_data is not None:
            name = inline_data.display_name or "uploaded attachment"
            consumed_names.add(name)
            try:
                text = await asyncio.to_thread(
                    _extract_attachment,
                    name,
                    inline_data.mime_type or "",
                    inline_data.data or b"",
                )
                reports.append((name, text))
            except Exception:
                reports.append((name, "Text extraction failed."))
            continue

        file_data = getattr(part, "file_data", None)
        if file_data is not None:
            if file_data.display_name:
                artifact_names.append(file_data.display_name)
            continue

        text = getattr(part, "text", None)
        if text:
            artifact_names.extend(_ARTIFACT_MARKER.findall(text))
            retained_text = _ARTIFACT_MARKER.sub("", text).strip()
            if retained_text:
                retained_parts.append(types.Part(text=retained_text))

    for name in dict.fromkeys(artifact_names):
        if name in consumed_names:
            continue
        try:
            artifact = await _load_artifact(invocation_context, name)
            if artifact is None or artifact.inline_data is None:
                raise ValueError("the uploaded artifact could not be loaded")
            text = await asyncio.to_thread(
                _extract_attachment,
                name,
                artifact.inline_data.mime_type or "",
                artifact.inline_data.data or b"",
            )
            reports.append((name, text))
        except Exception:
            reports.append((name, "Text extraction failed."))

    attachment_text = "\n\n".join(
        f"Attachment {index + 1}:\n{text or 'No readable text was extracted.'}"
        for index, (_, text) in enumerate(reports)
    )[:_MAX_OUTPUT_CHARACTERS]
    attachment_json = json.dumps(
        {"attachment_evidence": attachment_text},
        ensure_ascii=False,
    )
    retained_parts.append(
        types.Part(
            text=(
                "[BEGIN UNTRUSTED ATTACHMENT DATA (JSON)]\n"
                f"{attachment_json}\n"
                "[END UNTRUSTED ATTACHMENT DATA]"
            )
        )
    )
    prepared_content = types.Content(
        role=user_content.role,
        parts=list(retained_parts),
    )
    invocation_context.user_content = prepared_content
    for event in invocation_context.session.events:
        if (
            event.author == "user"
            and event.invocation_id == invocation_context.invocation_id
            and event.content
        ):
            event.content.parts = list(prepared_content.parts)
    return prepared_content