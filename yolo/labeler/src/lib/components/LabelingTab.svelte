<script lang="ts">
  import CameraFeed from './CameraFeed.svelte';
  import FrameList from './FrameList.svelte';
  import LabelingInterface from './LabelingInterface.svelte';
  import { selectFrame, getCapturedFrames } from '../stores/labeling.svelte';

  function handleFrameCaptured(frameId: string) {
    const index = getCapturedFrames().length - 1;
    selectFrame(index);
  }
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
  <div class="space-y-8">
    <div class="bg-white rounded-lg shadow-md p-6">
      <h2 class="text-xl font-semibold mb-4">Camera Feed</h2>
      <CameraFeed onFrameCaptured={handleFrameCaptured} />
    </div>

    <div class="bg-white rounded-lg shadow-md p-6">
      <FrameList />
    </div>
  </div>

  <div class="bg-white rounded-lg shadow-md p-6">
    <LabelingInterface />
  </div>
</div>