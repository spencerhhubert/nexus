<script lang="ts">
  import { CLASS_NAMES, CLASS_COLORS } from '../constants';

  interface Dataset {
    filename: string;
    timestamp: string;
    imagePath: string;
    labelPath: string;
    labelCount: number;
    fileSize: number;
    lastModified: string;
  }

  interface Label {
    classId: number;
    points: { x: number; y: number }[];
  }

  interface Props {
    dataset: Dataset | null;
  }

  let { dataset }: Props = $props();
  let labels: Label[] = $state([]);
  let imageElement: HTMLImageElement | undefined = $state();
  let canvasElement: HTMLCanvasElement | undefined = $state();
  let containerElement: HTMLDivElement | undefined = $state();
  let loading = $state(false);

  async function loadLabels() {
    if (!dataset) return;

    loading = true;
    try {
      const response = await fetch(dataset.labelPath);
      const data = await response.json();
      labels = data.labels || [];
    } catch (error) {
      console.error('Error loading labels:', error);
      labels = [];
    } finally {
      loading = false;
    }
  }

  function drawLabels() {
    if (!imageElement || !canvasElement || !containerElement) return;

    const canvas = canvasElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = imageElement;
    const container = containerElement;

    // Calculate the display size of the image
    const containerRect = container.getBoundingClientRect();
    const maxWidth = containerRect.width;
    const maxHeight = containerRect.height;

    let displayWidth, displayHeight;
    const aspectRatio = img.naturalWidth / img.naturalHeight;

    if (maxWidth / aspectRatio <= maxHeight) {
      displayWidth = maxWidth;
      displayHeight = maxWidth / aspectRatio;
    } else {
      displayHeight = maxHeight;
      displayWidth = maxHeight * aspectRatio;
    }

    // Set canvas size to match displayed image size
    canvas.width = displayWidth;
    canvas.height = displayHeight;
    canvas.style.width = displayWidth + 'px';
    canvas.style.height = displayHeight + 'px';

    // Set image size to match
    img.style.width = displayWidth + 'px';
    img.style.height = displayHeight + 'px';

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (labels.length === 0) return;

    labels.forEach(label => {
      const className = CLASS_NAMES[label.classId] || 'object';
      const color = CLASS_COLORS[className as keyof typeof CLASS_COLORS] || '#ef4444';

      if (label.points.length < 3) return;

      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.fillStyle = color + '30';
      ctx.lineWidth = 2;

      const firstPoint = label.points[0];
      ctx.moveTo(firstPoint.x * displayWidth, firstPoint.y * displayHeight);

      for (let i = 1; i < label.points.length; i++) {
        const point = label.points[i];
        ctx.lineTo(point.x * displayWidth, point.y * displayHeight);
      }

      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      const centerX = label.points.reduce((sum, p) => sum + p.x, 0) / label.points.length * displayWidth;
      const centerY = label.points.reduce((sum, p) => sum + p.y, 0) / label.points.length * displayHeight;

      ctx.fillStyle = '#fff';
      ctx.strokeStyle = '#000';
      ctx.font = '14px Arial';
      ctx.textAlign = 'center';
      ctx.lineWidth = 3;
      ctx.strokeText(className, centerX, centerY);
      ctx.fillText(className, centerX, centerY);
    });
  }

  function onImageLoad() {
    // Small delay to ensure container dimensions are available
    setTimeout(drawLabels, 10);
  }

  function handleResize() {
    drawLabels();
  }

  $effect(() => {
    if (dataset) {
      loadLabels();
    }
  });

  $effect(() => {
    if (labels.length >= 0 && imageElement && containerElement) {
      drawLabels();
    }
  });
</script>

{#if dataset}
  <div class="h-full flex flex-col">
    <div class="mb-4">
      <h3 class="text-lg font-semibold text-gray-900">{dataset.filename}</h3>
      <div class="flex items-center gap-4 text-sm text-gray-500">
        <span>{dataset.labelCount} label{dataset.labelCount !== 1 ? 's' : ''}</span>
        <span>{new Date(dataset.lastModified).toLocaleString()}</span>
      </div>
    </div>

    {#if loading}
      <div class="flex-1 flex items-center justify-center">
        <div class="text-gray-500">Loading labels...</div>
      </div>
    {:else}
      <div bind:this={containerElement} class="flex-1 flex items-center justify-center rounded-lg border bg-gray-50 min-h-0">
        <div class="relative max-w-full max-h-full">
          <img
            bind:this={imageElement}
            src={dataset.imagePath}
            alt="Dataset {dataset.filename}"
            class="block max-w-full max-h-full object-contain"
            onload={onImageLoad}
          />
          <canvas
            bind:this={canvasElement}
            class="absolute top-0 left-0 pointer-events-none"
          ></canvas>
        </div>
      </div>

      {#if labels.length > 0}
        <div class="mt-4 space-y-2 flex-shrink-0">
          <h4 class="font-medium text-gray-900">Labels:</h4>
          <div class="flex flex-wrap gap-2">
            {#each labels as label}
              {@const className = CLASS_NAMES[label.classId] || 'object'}
              {@const color = CLASS_COLORS[className as keyof typeof CLASS_COLORS] || '#ef4444'}
              <div class="flex items-center gap-2 px-3 py-1 rounded-full border text-sm">
                <div
                  class="w-3 h-3 rounded-full"
                  style="background-color: {color}"
                ></div>
                <span>{className}</span>
                <span class="text-gray-500">({label.points.length} pts)</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}
  </div>
{:else}
  <div class="h-full flex items-center justify-center">
    <div class="text-center text-gray-500">
      <p>Select a dataset to view</p>
      <p class="text-sm mt-1">Choose from the list on the left</p>
    </div>
  </div>
{/if}