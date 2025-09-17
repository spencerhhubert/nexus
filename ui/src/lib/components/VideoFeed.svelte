<script lang="ts">
  import { getPageState } from '$lib/stores/page-state.svelte';
  import { Camera, Wifi, WifiOff } from 'lucide-svelte';

  interface Props {
    camera: 'main_camera' | 'feeder_camera';
    title: string;
  }

  let { camera, title }: Props = $props();

  const pageState = getPageState();

  const frame = $derived(() => {
    return camera === 'main_camera'
      ? pageState.state.mainCameraFrame
      : pageState.state.feederCameraFrame;
  });

  const imageSrc = $derived(() => {
    const currentFrame = frame();
    return currentFrame ? `data:image/jpeg;base64,${currentFrame.data}` : null;
  });

  const lastUpdate = $derived(() => {
    const currentFrame = frame();
    return currentFrame ? new Date(currentFrame.timestamp).toLocaleTimeString() : 'No data';
  });
</script>

<div class="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700">
  <div class="flex justify-between items-center mb-4">
    <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
    <span class="text-sm text-gray-500 dark:text-gray-400">
      Last: {lastUpdate()}
    </span>
  </div>

  <div class="relative bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600" style="aspect-ratio: 4/3;">
    {#if imageSrc()}
      <img
        src={imageSrc()}
        alt="{title} feed"
        class="w-full h-full object-cover"
      />
    {:else}
      <div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        <div class="text-center">
          <Camera size={48} class="mx-auto mb-2" />
          <div>No video feed</div>
          {#if !pageState.state.wsConnected}
            <div class="text-sm mt-1">WebSocket disconnected</div>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <div class="mt-2 flex justify-between text-xs text-gray-500 dark:text-gray-400">
    <span>Camera: {camera}</span>
    <span class="flex items-center gap-1">
      {#if pageState.state.wsConnected}
        <Wifi size={12} class="text-green-500" />
        <span>Connected</span>
      {:else}
        <WifiOff size={12} class="text-red-500" />
        <span>Disconnected</span>
      {/if}
    </span>
  </div>
</div>