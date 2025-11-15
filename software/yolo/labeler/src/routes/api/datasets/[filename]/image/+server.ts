import type { RequestHandler } from './$types';
// @ts-ignore
import { readFile } from 'fs/promises';
// @ts-ignore
import path from 'path';

const DATA_DIR = '/Users/spencer/Documents/GitHub/nexus2/yolo/labeler/data';

export const GET: RequestHandler = async ({ params }) => {
  try {
    const { filename } = params;
    const imagePath = path.join(DATA_DIR, `${filename}.jpg`);

    const imageBuffer = await readFile(imagePath);

    return new Response(imageBuffer, {
      headers: {
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'public, max-age=3600'
      }
    });
  } catch (error) {
    console.error('Error serving image:', error);
    return new Response('Image not found', { status: 404 });
  }
};