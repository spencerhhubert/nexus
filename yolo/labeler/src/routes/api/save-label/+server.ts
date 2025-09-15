import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
// @ts-ignore
import { writeFile, mkdir } from 'fs/promises';
// @ts-ignore
import path from 'path';

const DATA_DIR = '/Users/spencer/Documents/GitHub/nexus2/yolo/labeler/data';

export const POST: RequestHandler = async ({ request }) => {
  try {
    const { imageData, labels, timestamp } = await request.json();

    // Ensure data directory exists
    await mkdir(DATA_DIR, { recursive: true });

    const filename = `${timestamp}`;
    const imagePath = path.join(DATA_DIR, `${filename}.jpg`);
    const labelPath = path.join(DATA_DIR, `${filename}.txt`);

    // Save image (convert base64 to buffer)
    // @ts-ignore
    const imageBuffer = Buffer.from(imageData.split(',')[1], 'base64');
    console.log(`Saving image: ${filename}.jpg, size: ${imageBuffer.length} bytes`);
    await writeFile(imagePath, imageBuffer);

    // Save labels in YOLO format
    const labelText = labels.map((label: any) => {
      const points = label.points.map((p: any) => `${p.x} ${p.y}`).join(' ');
      return `${label.classId} ${points}`;
    }).join('\n');

    await writeFile(labelPath, labelText);

    return json({ success: true, filename, timestamp });
  } catch (error) {
    console.error('Error saving label:', error);
    return json({ error: 'Failed to save label' }, { status: 500 });
  }
};