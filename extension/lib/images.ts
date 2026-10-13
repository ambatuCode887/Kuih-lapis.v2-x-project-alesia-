export const MAX_IMAGES = 4;
const MAX_SOURCE_BYTES = 20 * 1024 * 1024; // matches the backend's 20 MB limit
const MAX_EDGE = 1600;

export function isImageFile(file: File): boolean {
  return file.type.startsWith('image/');
}

/**
 * Turn an image file into a compressed data URL. Large screenshots are scaled
 * down so they stay small in storage and still read clearly for OCR.
 */
export async function prepareImage(file: File): Promise<string> {
  if (!isImageFile(file)) throw new Error('That file is not an image.');
  if (file.size > MAX_SOURCE_BYTES) throw new Error('Images larger than 20 MB are not supported.');

  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
  const width = Math.max(1, Math.round(bitmap.width * scale));
  const height = Math.max(1, Math.round(bitmap.height * scale));

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d');
  if (!context) throw new Error('Could not read that image.');
  // JPEG has no transparency, so paint a white background first.
  context.fillStyle = '#ffffff';
  context.fillRect(0, 0, width, height);
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();

  return canvas.toDataURL('image/jpeg', 0.88);
}

/** Split a data URL into its MIME type and base64 payload. */
export function splitDataUrl(dataUrl: string): { mimeType: string; data: string } {
  const match = dataUrl.match(/^data:([^;,]+);base64,(.*)$/);
  return { mimeType: match?.[1] ?? 'image/jpeg', data: match?.[2] ?? '' };
}
