import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
// @ts-ignore
import { readdir, readFile, stat } from 'fs/promises';
// @ts-ignore
import path from 'path';

const DATA_DIR = '/Users/spencer/Documents/GitHub/nexus2/yolo/labeler/data';

interface Dataset {
  filename: string;
  timestamp: string;
  imagePath: string;
  labelPath: string;
  labelCount: number;
  fileSize: number;
  lastModified: Date;
}

export const GET: RequestHandler = async () => {
  try {
    const files = await readdir(DATA_DIR);
    const imageFiles = files.filter(file => file.endsWith('.jpg'));

    const datasets: Dataset[] = [];

    for (const imageFile of imageFiles) {
      const baseName = path.parse(imageFile).name;
      const labelFile = `${baseName}.txt`;

      const imagePath = path.join(DATA_DIR, imageFile);
      const labelPath = path.join(DATA_DIR, labelFile);

      try {
        // Check if corresponding label file exists
        const imageStats = await stat(imagePath);
        await stat(labelPath); // This will throw if file doesn't exist

        // Read label file to count labels
        const labelContent = await readFile(labelPath, 'utf-8');
        const labelCount = labelContent.trim() ? labelContent.trim().split('\n').length : 0;

        datasets.push({
          filename: baseName,
          timestamp: baseName,
          imagePath: `/api/datasets/${baseName}/image`,
          labelPath: `/api/datasets/${baseName}/labels`,
          labelCount,
          fileSize: imageStats.size,
          lastModified: imageStats.mtime
        });
      } catch (error) {
        // Skip if label file doesn't exist
        continue;
      }
    }

    // Sort by timestamp (newest first)
    datasets.sort((a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime());

    return json({ datasets });
  } catch (error) {
    console.error('Error fetching datasets:', error);
    return json({ error: 'Failed to fetch datasets' }, { status: 500 });
  }
};