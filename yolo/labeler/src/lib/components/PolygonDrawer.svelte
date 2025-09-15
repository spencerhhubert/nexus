<script lang="ts">
  import { CLASS_NAMES, CLASS_COLORS, type ClassName } from '../constants.js';
  import type { Point, Label } from '../utils/polygon.js';
  import { normalizePoints } from '../utils/polygon.js';
  import { getSelectedClassId, addLabelToCurrentFrameAndMarkUnsaved, setSelectedClassId } from '../stores/labeling.svelte';

  let isDrawing = $state(false);
  let localSelectedClassId = $state(getSelectedClassId());

  // Sync local state with global state
  $effect(() => {
    setSelectedClassId(localSelectedClassId);
  });

  let { imageData, labels = [], selectedLabelIndices = [] }: {
    imageData: string;
    labels?: Label[];
    selectedLabelIndices?: number[];
  } = $props();

  let canvas = $state<HTMLCanvasElement>();
  let img = $state<HTMLImageElement>();
  let currentPoints = $state<Point[]>([]);

  function setupCanvas() {
    if (!canvas || !img) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    canvas.style.width = '100%';
    canvas.style.height = 'auto';

    redrawCanvas();
  }

  function redrawCanvas() {
    if (!canvas || !img) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    // Draw existing labels (outlines only)
    labels.forEach((label, index) => {
      if (label.points.length > 0 && !selectedLabelIndices.includes(index)) {
        drawPolygon(ctx, label.points, CLASS_COLORS[label.className as ClassName], label.isComplete, false);
      }
    });

    // Draw selected labels with overlay
    selectedLabelIndices.forEach(index => {
      const label = labels[index];
      if (label && label.points.length > 0) {
        drawPolygon(ctx, label.points, CLASS_COLORS[label.className as ClassName], label.isComplete, true);
      }
    });

    // Draw current polygon being drawn (these are canvas coordinates, not normalized)
    if (currentPoints.length > 0) {
      const currentColor = CLASS_COLORS[CLASS_NAMES[localSelectedClassId]];
      drawCurrentPolygon(ctx, currentPoints, currentColor);
    }
  }

  function drawCurrentPolygon(ctx: CanvasRenderingContext2D, points: Point[], color: string) {
    if (points.length === 0) return;

    ctx.strokeStyle = color;
    ctx.fillStyle = color + '40'; // 25% opacity
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.stroke();

    // Draw points
    points.forEach((point, index) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
      ctx.fill();

      // Draw point number
      ctx.fillStyle = 'white';
      ctx.font = '12px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(index.toString(), point.x, point.y + 4);
    });
  }

  function drawPolygon(ctx: CanvasRenderingContext2D, points: Point[], color: string, isComplete: boolean, isSelected: boolean = false) {
    if (points.length === 0) return;

    const denormalizedPoints = points.map(p => ({
      x: p.x * (canvas?.width || 1),
      y: p.y * (canvas?.height || 1)
    }));

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;

    // Set fill opacity based on selection
    if (isSelected) {
      ctx.fillStyle = color + '60'; // 37% opacity for selected
    } else {
      ctx.fillStyle = color + '20'; // 12% opacity for unselected
    }

    ctx.beginPath();
    ctx.moveTo(denormalizedPoints[0].x, denormalizedPoints[0].y);
    for (let i = 1; i < denormalizedPoints.length; i++) {
      ctx.lineTo(denormalizedPoints[i].x, denormalizedPoints[i].y);
    }

    if (isComplete) {
      ctx.closePath();
      if (isSelected) {
        ctx.fill(); // Only fill selected labels
      }
    }
    ctx.stroke();

    // Draw points (more prominent for selected labels)
    denormalizedPoints.forEach((point, index) => {
      ctx.fillStyle = color;
      ctx.beginPath();
      const radius = isSelected ? 6 : 4;
      ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
      ctx.fill();

      // Draw point number
      ctx.fillStyle = isSelected ? 'white' : 'black';
      ctx.font = isSelected ? '14px Arial' : '12px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(index.toString(), point.x, point.y + (isSelected ? 5 : 4));
    });
  }

  function getCanvasPoint(event: MouseEvent): Point {
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    return {
      x: (event.clientX - rect.left) * scaleX,
      y: (event.clientY - rect.top) * scaleY
    };
  }

  function handleCanvasClick(event: MouseEvent) {
    const point = getCanvasPoint(event);

    if (isDrawing) {
      currentPoints.push(point);
      redrawCanvas();
    }
  }

  function handleCanvasDoubleClick() {
    if (currentPoints.length >= 3) {
      const normalizedPoints = normalizePoints(currentPoints, canvas?.width || 1, canvas?.height || 1);

      const label: Label = {
        classId: localSelectedClassId,
        className: CLASS_NAMES[localSelectedClassId],
        points: normalizedPoints,
        isComplete: true
      };

      addLabelToCurrentFrameAndMarkUnsaved(label);
      currentPoints = [];
      isDrawing = false;
      redrawCanvas();
    }
  }

  function startDrawing() {
    isDrawing = true;
    currentPoints = [];
  }

  function cancelDrawing() {
    isDrawing = false;
    currentPoints = [];
    redrawCanvas();
  }

  $effect(() => {
    if (img && imageData) {
      img.src = imageData;
    }
  });

  $effect(() => {
    redrawCanvas();
  });
</script>

<div class="space-y-4">
  <div class="flex items-center gap-4">
    <div class="flex flex-col gap-2">
      <label for="class-select" class="text-sm font-medium">Class:</label>
      <select
        id="class-select"
        bind:value={localSelectedClassId}
        class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {#each CLASS_NAMES as className, index}
          <option value={index}>{className}</option>
        {/each}
      </select>
    </div>

    <div class="flex gap-2">
      <button
        onclick={startDrawing}
        disabled={isDrawing}
        class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Start Drawing
      </button>

      <button
        onclick={cancelDrawing}
        disabled={!isDrawing}
        class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Cancel
      </button>
    </div>
  </div>

  <div class="relative">
    <img
      bind:this={img}
      onload={setupCanvas}
      alt="Frame to label"
      class="hidden"
    />

    <canvas
      bind:this={canvas}
      onclick={handleCanvasClick}
      ondblclick={handleCanvasDoubleClick}
      class="border border-gray-300 rounded-lg cursor-crosshair max-w-full"
    ></canvas>
  </div>

  <div class="text-sm text-gray-600">
    {#if isDrawing}
      <p>Click to add points, double-click to complete polygon ({currentPoints.length} points)</p>
    {:else}
      <p>Select a class and click "Start Drawing" to begin labeling</p>
    {/if}
  </div>
</div>