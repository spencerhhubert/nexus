import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
// @ts-ignore
import { readFile } from 'fs/promises';
// @ts-ignore
import path from 'path';

const DATA_DIR = '/Users/spencer/Documents/GitHub/nexus2/yolo/labeler/data';

export const GET: RequestHandler = async ({ params }) => {
  try {
    const { filename } = params;
    const labelPath = path.join(DATA_DIR, `${filename}.txt`);

    const labelContent = await readFile(labelPath, 'utf-8');
    const lines = labelContent.trim().split('\n').filter(line => line.trim());

    const labels = lines.map(line => {
      const parts = line.trim().split(' ');
      const classId = parseInt(parts[0]);
      const points = [];

      for (let i = 1; i < parts.length; i += 2) {
        if (i + 1 < parts.length) {
          points.push({
            x: parseFloat(parts[i]),
            y: parseFloat(parts[i + 1])
          });
        }
      }

      return {
        classId,
        points
      };
    });

    return json({ labels });
  } catch (error) {
    console.error('Error serving labels:', error);
    return json({ error: 'Labels not found' }, { status: 404 });
  }
};