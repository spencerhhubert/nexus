<script lang="ts">
  import { onMount } from 'svelte';
  import { observationsForCurrentFrame } from '$lib/stores/app';

  interface Props {
    cameraFrame: string | null;
  }

  let { cameraFrame }: Props = $props();
  let canvasEl = $state<HTMLCanvasElement>();
  let imageEl = $state<HTMLImageElement>();

  function drawBoundingBoxes() {
    if (!canvasEl || !imageEl || !$observationsForCurrentFrame.length) return;
    
    const ctx = canvasEl.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
    
    // Draw the image
    ctx.drawImage(imageEl, 0, 0, canvasEl.width, canvasEl.height);
    
    // Draw bounding boxes
    ctx.strokeStyle = 'lime';
    ctx.lineWidth = 2;
    ctx.font = '12px Arial';
    ctx.fillStyle = 'lime';
    
    for (const obs of $observationsForCurrentFrame) {
      const x = obs.center_x_percent * canvasEl.width - (obs.bbox_width_percent * canvasEl.width) / 2;
      const y = obs.center_y_percent * canvasEl.height - (obs.bbox_height_percent * canvasEl.height) / 2;
      const w = obs.bbox_width_percent * canvasEl.width;
      const h = obs.bbox_height_percent * canvasEl.height;
      
      ctx.strokeRect(x, y, w, h);
      
      // Draw classification text
      const classification = obs.classification_result?.data?.item_id || 'unknown';
      ctx.fillText(classification, x, y - 5);
    }
  }

  function handleImageLoad() {
    if (!canvasEl || !imageEl) return;
    
    canvasEl.width = imageEl.naturalWidth;
    canvasEl.height = imageEl.naturalHeight;
    drawBoundingBoxes();
  }

  $effect(() => {
    if (cameraFrame || $observationsForCurrentFrame) {
      // Trigger redraw when camera frame or observations change
      drawBoundingBoxes();
    }
  });
</script>

<section class="bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700 p-5 h-full flex flex-col">
  <h2 class="text-xl font-semibold text-foreground-light dark:text-foreground-dark mb-5 pb-3 border-b border-surface-200 dark:border-surface-700">
    Camera Feed
  </h2>

  <div class="bg-surface-100 dark:bg-surface-900 flex-1 flex items-center justify-center relative">
    {#if cameraFrame}
      <div class="relative max-w-full max-h-full">
        <!-- Hidden image for loading -->
        <img
          bind:this={imageEl}
          src="data:image/jpeg;base64,{cameraFrame}"
          alt="Camera feed"
          class="hidden"
          onload={handleImageLoad}
        />
        
        <!-- Canvas for drawing bounding boxes -->
        <canvas
          bind:this={canvasEl}
          class="max-w-full max-h-full border border-gray-300"
        ></canvas>
      </div>
    {:else}
      <div class="text-surface-500 dark:text-surface-400 italic">No camera feed</div>
    {/if}
  </div>
</section>
