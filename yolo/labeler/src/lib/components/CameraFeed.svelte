<script lang="ts">
  import { onMount } from 'svelte';
  import { getCameraDevices, startCamera, captureFrame } from '../utils/camera.js';
  import { addFrame } from '../stores/labeling.svelte';

  let { onFrameCaptured }: { onFrameCaptured?: (frameId: string) => void } = $props();

  let devices = $state<MediaDeviceInfo[]>([]);
  let selectedDeviceId = $state<string>('');
  let stream = $state<MediaStream | null>(null);
  let videoElement = $state<HTMLVideoElement>();
  let isStreaming = $state(false);

  onMount(async () => {
    console.log('Loading camera devices...');
    devices = await getCameraDevices();
    console.log('Devices loaded:', devices.length);

    if (devices.length > 0) {
      selectedDeviceId = devices[0].deviceId;
      console.log('Selected device:', devices[0]);
    } else {
      console.warn('No camera devices found');
    }
  });

  async function startStream() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }

    stream = await startCamera(selectedDeviceId);
    if (stream && videoElement) {
      videoElement.srcObject = stream;
      isStreaming = true;
    }
  }

  async function stopStream() {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      stream = null;
      isStreaming = false;
    }
  }

  async function refreshDevices() {
    console.log('Refreshing camera devices...');
    devices = await getCameraDevices();
    console.log('Devices refreshed:', devices.length);

    if (devices.length > 0 && !selectedDeviceId) {
      selectedDeviceId = devices[0].deviceId;
    }
  }

  function handleCapture() {
    if (videoElement && isStreaming) {
      const imageData = captureFrame(videoElement);
      const frameId = addFrame(imageData);
      onFrameCaptured?.(frameId);
    }
  }
</script>

<div class="space-y-4">
  <div class="flex flex-col gap-2">
    <div class="flex items-center gap-2">
      <label for="camera-select" class="text-sm font-medium">Select Camera</label>
      <button
        onclick={refreshDevices}
        class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
        title="Refresh camera list"
      >
        🔄
      </button>
    </div>
    <select
      id="camera-select"
      bind:value={selectedDeviceId}
      class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {#if devices.length === 0}
        <option value="">No cameras found</option>
      {:else}
        {#each devices as device}
          <option value={device.deviceId}>
            {device.label || `Camera ${device.deviceId.slice(0, 8)}`}
          </option>
        {/each}
      {/if}
    </select>
  </div>

  <div class="flex gap-2">
    <button
      onclick={startStream}
      disabled={!selectedDeviceId || isStreaming}
      class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      Start Camera
    </button>

    <button
      onclick={stopStream}
      disabled={!isStreaming}
      class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      Stop Camera
    </button>

    <button
      onclick={handleCapture}
      disabled={!isStreaming}
      class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      Capture Frame
    </button>
  </div>

  <div class="relative">
    <video
      bind:this={videoElement}
      autoplay
      playsinline
      class="w-full max-w-2xl border border-gray-300 rounded-lg {isStreaming ? '' : 'hidden'}"
    >
      <track kind="captions" />
    </video>

    {#if !isStreaming}
      <div class="w-full max-w-2xl h-60 border border-gray-300 rounded-lg bg-gray-100 flex items-center justify-center">
        <p class="text-gray-500">Camera not active</p>
      </div>
    {/if}
  </div>
</div>