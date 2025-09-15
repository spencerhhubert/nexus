import type { Label } from '../utils/polygon.js';

interface CapturedFrame {
  id: string;
  imageData: string;
  timestamp: number;
  labels: Label[];
  isSaved: boolean;
  savedTimestamp?: number;
}

let capturedFrames = $state<CapturedFrame[]>([]);
let currentFrameIndex = $state<number | null>(null);
let selectedClassId = $state<number>(0);

export function getCapturedFrames() {
  return capturedFrames;
}

export function getCurrentFrameIndex() {
  return currentFrameIndex;
}

export function getSelectedClassId() {
  return selectedClassId;
}

export function setSelectedClassId(id: number) {
  selectedClassId = id;
}

export function setCurrentFrameIndex(index: number | null) {
  currentFrameIndex = index;
}

export function addFrame(imageData: string): string {
  const id = `frame_${Date.now()}`;
  const frame: CapturedFrame = {
    id,
    imageData,
    timestamp: Date.now(),
    labels: [],
    isSaved: false
  };
  capturedFrames.push(frame);
  return id;
}

export function selectFrame(index: number) {
  setCurrentFrameIndex(index);
}

export function getCurrentFrame(): CapturedFrame | null {
  return currentFrameIndex !== null ? capturedFrames[currentFrameIndex] : null;
}

export function addLabelToCurrentFrame(label: Label) {
  const frame = getCurrentFrame();
  if (frame) {
    frame.labels.push(label);
  }
}

export function removeLabelFromCurrentFrame(labelIndex: number) {
  const frame = getCurrentFrame();
  if (frame) {
    frame.labels.splice(labelIndex, 1);
    // Mark as unsaved when labels change
    frame.isSaved = false;
    frame.savedTimestamp = undefined;
  }
}

export function markFrameAsSaved(frameIndex: number, savedTimestamp: number) {
  const frame = capturedFrames[frameIndex];
  if (frame) {
    frame.isSaved = true;
    frame.savedTimestamp = savedTimestamp;
  }
}

export function addLabelToCurrentFrameAndMarkUnsaved(label: Label) {
  const frame = getCurrentFrame();
  if (frame) {
    frame.labels.push(label);
    // Mark as unsaved when labels change
    frame.isSaved = false;
    frame.savedTimestamp = undefined;
  }
}