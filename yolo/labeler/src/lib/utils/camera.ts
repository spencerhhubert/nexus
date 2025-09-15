export async function getCameraDevices(): Promise<MediaDeviceInfo[]> {
  try {
    // First, request camera permission to get device labels
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      // Stop the stream immediately, we just needed permission
      stream.getTracks().forEach(track => track.stop());
    } catch (permissionError) {
      console.warn('Camera permission not granted:', permissionError);
    }

    // Now enumerate devices (should have labels if permission granted)
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === 'videoinput');

    console.log('Found video devices:', videoDevices);
    return videoDevices;
  } catch (error) {
    console.error('Error getting camera devices:', error);
    return [];
  }
}

export async function startCamera(deviceId?: string): Promise<MediaStream | null> {
  try {
    const constraints: MediaStreamConstraints = {
      video: deviceId ? { deviceId } : true,
      audio: false
    };
    return await navigator.mediaDevices.getUserMedia(constraints);
  } catch (error) {
    console.error('Error starting camera:', error);
    return null;
  }
}

export function captureFrame(video: HTMLVideoElement): string {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Could not get canvas context');

  ctx.drawImage(video, 0, 0);
  return canvas.toDataURL('image/jpeg', 0.8);
}