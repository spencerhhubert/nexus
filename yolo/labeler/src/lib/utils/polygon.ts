export interface Point {
  x: number;
  y: number;
}

export interface Label {
  classId: number;
  className: string;
  points: Point[];
  isComplete: boolean;
}

export function normalizePoints(points: Point[], imageWidth: number, imageHeight: number): Point[] {
  return points.map(p => ({
    x: p.x / imageWidth,
    y: p.y / imageHeight
  }));
}

export function denormalizePoints(points: Point[], imageWidth: number, imageHeight: number): Point[] {
  return points.map(p => ({
    x: p.x * imageWidth,
    y: p.y * imageHeight
  }));
}

export function isPointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    if (((polygon[i].y > point.y) !== (polygon[j].y > point.y)) &&
        (point.x < (polygon[j].x - polygon[i].x) * (point.y - polygon[i].y) / (polygon[j].y - polygon[i].y) + polygon[i].x)) {
      inside = !inside;
    }
  }
  return inside;
}

export function getPolygonCenter(points: Point[]): Point {
  const sumX = points.reduce((sum, p) => sum + p.x, 0);
  const sumY = points.reduce((sum, p) => sum + p.y, 0);
  return {
    x: sumX / points.length,
    y: sumY / points.length
  };
}