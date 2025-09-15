<script lang="ts">
  import CameraFeed from '$lib/components/CameraFeed.svelte';
  import FrameList from '$lib/components/FrameList.svelte';
  import LabelingInterface from '$lib/components/LabelingInterface.svelte';
  import { selectFrame, getCapturedFrames } from '$lib/stores/labeling.svelte';

  function handleFrameCaptured(frameId: string) {
    // Auto-select the newly captured frame
    const index = getCapturedFrames().length - 1;
    selectFrame(index);
  }
</script>

<svelte:head>
  <title>YOLO Labeler</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold text-gray-900 mb-8">YOLO Labeler</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Left Column: Camera and Frame List -->
      <div class="space-y-8">
        <div class="bg-white rounded-lg shadow-md p-6">
          <h2 class="text-xl font-semibold mb-4">Camera Feed</h2>
          <CameraFeed onFrameCaptured={handleFrameCaptured} />
        </div>

        <div class="bg-white rounded-lg shadow-md p-6">
          <FrameList />
        </div>
      </div>

      <!-- Right Column: Labeling Interface -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <LabelingInterface />
      </div>
    </div>
  </div>
</div>