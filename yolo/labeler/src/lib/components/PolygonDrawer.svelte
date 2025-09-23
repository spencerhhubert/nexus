<script lang="ts">
  import { CLASS_NAMES, CLASS_COLORS, type ClassName } from "../constants.js";
  import type { Point, Label } from "../utils/polygon.js";
  import { normalizePoints } from "../utils/polygon.js";
  import {
    getSelectedClassId,
    addLabelToCurrentFrameAndMarkUnsaved,
    setSelectedClassId,
    getIsDrawing,
    startDrawing,
    stopDrawing,
  } from "../stores/labeling.svelte";

  let isDrawing = $derived(getIsDrawing());
  let selectedClassId = $derived(getSelectedClassId());
  let hoverNearFirst = $state(false); // For hover feedback
  let warningMessage = $state<string>(""); // For UI warnings

  // Auto-start drawing when class changes (but not on initial load)
  let previousClassId = $state<number | undefined>(undefined);
  $effect(() => {
    if (
      previousClassId !== undefined &&
      previousClassId !== selectedClassId
    ) {
      if (!isDrawing) {
        startDrawing();
      }
    }
    previousClassId = selectedClassId;
  });

  let {
    imageData,
    labels = [],
    selectedLabelIndices = [],
    fullscreen = false,
  }: {
    imageData: string;
    labels?: Label[];
    selectedLabelIndices?: number[];
    fullscreen?: boolean;
  } = $props();

  let canvas = $state<HTMLCanvasElement>();
  let img = $state<HTMLImageElement>();
  let currentPoints = $state<Point[]>([]);

  const DISTANCE_THRESHOLD = fullscreen ? 8 : 5; // pixels for duplicate/hover
  const AREA_THRESHOLD = fullscreen ? 15 : 10; // min area in pixels^2

  function distance(p1: Point, p2: Point): number {
    return Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);
  }

  function segmentsIntersect(
    p1: Point,
    p2: Point,
    p3: Point,
    p4: Point,
  ): boolean {
    const ccw = (A: Point, B: Point, C: Point) =>
      (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x);
    return (
      ccw(p1, p3, p4) !== ccw(p2, p3, p4) && ccw(p1, p2, p3) !== ccw(p1, p2, p4)
    );
  }

  function wouldIntersect(newPoint: Point): boolean {
    if (currentPoints.length < 2) return false;
    const n = currentPoints.length;
    const newEdgeStart = currentPoints[n - 1];
    for (let i = 0; i < n - 2; i++) {
      const edgeStart = currentPoints[i];
      const edgeEnd = currentPoints[i + 1];
      if (segmentsIntersect(newEdgeStart, newPoint, edgeStart, edgeEnd)) {
        return true;
      }
    }
    return false;
  }

  function shoelaceArea(points: Point[]): number {
    let area = 0;
    for (let i = 0; i < points.length; i++) {
      const x1 = points[i].x;
      const y1 = points[i].y;
      const x2 = points[(i + 1) % points.length].x;
      const y2 = points[(i + 1) % points.length].y;
      area += x1 * y2 - x2 * y1;
    }
    return Math.abs(area) / 2;
  }

  function setupCanvas() {
    if (!canvas || !img) return;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    canvas.style.width = "100%";
    canvas.style.height = "auto";

    redrawCanvas();
  }

  function redrawCanvas() {
    if (!canvas || !img) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    // Draw existing labels (outlines only)
    labels.forEach((label, index) => {
      if (label.points.length > 0 && !selectedLabelIndices.includes(index)) {
        drawPolygon(
          ctx,
          label.points,
          CLASS_COLORS[label.className as ClassName],
          label.isComplete,
          false,
        );
      }
    });

    // Draw selected labels with overlay
    selectedLabelIndices.forEach((index) => {
      const label = labels[index];
      if (label && label.points.length > 0) {
        drawPolygon(
          ctx,
          label.points,
          CLASS_COLORS[label.className as ClassName],
          label.isComplete,
          true,
        );
      }
    });

    // Draw current polygon being drawn
    if (currentPoints.length > 0) {
      const currentColor = CLASS_COLORS[CLASS_NAMES[selectedClassId]];
      drawCurrentPolygon(ctx, currentPoints, currentColor);
    }
  }

  function drawCurrentPolygon(
    ctx: CanvasRenderingContext2D,
    points: Point[],
    color: string,
  ) {
    if (points.length === 0) return;

    ctx.strokeStyle = color;
    ctx.fillStyle = color + "40"; // 25% opacity
    ctx.lineWidth = fullscreen ? 3 : 2;

    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i].x, points[i].y);
    }
    ctx.stroke();

    // Draw points
    points.forEach((point, index) => {
      ctx.fillStyle = index === 0 && hoverNearFirst ? "yellow" : color; // Highlight first on hover
      ctx.beginPath();
      const radius = index === 0 && hoverNearFirst ? 6 : 4;
      ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
      ctx.fill();

      // Draw point number
      ctx.fillStyle = "white";
      ctx.font = "12px Arial";
      ctx.textAlign = "center";
      ctx.fillText(index.toString(), point.x, point.y + 4);
    });
  }

  function drawPolygon(
    ctx: CanvasRenderingContext2D,
    points: Point[],
    color: string,
    isComplete: boolean,
    isSelected: boolean = false,
  ) {
    if (points.length === 0) return;

    const denormalizedPoints = points.map((p) => ({
      x: p.x * (canvas?.width || 1),
      y: p.y * (canvas?.height || 1),
    }));

    ctx.strokeStyle = color;
    ctx.lineWidth = fullscreen ? 3 : 2;

    // Set fill opacity based on selection
    if (isSelected) {
      ctx.fillStyle = color + "60"; // 37% opacity for selected
    } else {
      ctx.fillStyle = color + "20"; // 12% opacity for unselected
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
      const radius = fullscreen ? (isSelected ? 8 : 6) : (isSelected ? 6 : 4);
      ctx.arc(point.x, point.y, radius, 0, 2 * Math.PI);
      ctx.fill();

      // Draw point number
      ctx.fillStyle = isSelected ? "white" : "black";
      ctx.font = fullscreen ? (isSelected ? "16px Arial" : "14px Arial") : (isSelected ? "14px Arial" : "12px Arial");
      ctx.textAlign = "center";
      ctx.fillText(index.toString(), point.x, point.y + (isSelected ? 5 : 4));
    });
  }

  function getCanvasPoint(event: MouseEvent): Point {
    if (!canvas) return { x: 0, y: 0 };

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    let x = (event.clientX - rect.left) * scaleX;
    let y = (event.clientY - rect.top) * scaleY;

    // Clamp to [0, canvas dims]
    x = Math.max(0, Math.min(x, canvas.width));
    y = Math.max(0, Math.min(y, canvas.height));

    return { x, y };
  }

  function handleCanvasClick(event: MouseEvent) {
    if (!isDrawing) return;
    const point = getCanvasPoint(event);

    if (
      currentPoints.length >= 3 &&
      distance(point, currentPoints[0]) < DISTANCE_THRESHOLD
    ) {
      // Attempt to close
      const tempPoints = [...currentPoints]; // Don't close with repeat
      const area = shoelaceArea(tempPoints);
      if (area < AREA_THRESHOLD) {
        warningMessage =
          "Polygon has zero area (collinear points)! Cannot close.";
        setTimeout(() => (warningMessage = ""), 3000);
        return;
      }
      const normalizedPoints = normalizePoints(
        tempPoints,
        canvas?.width || 1,
        canvas?.height || 1,
      );
      const label: Label = {
        classId: selectedClassId,
        className: CLASS_NAMES[selectedClassId],
        points: normalizedPoints,
        isComplete: true,
      };
      addLabelToCurrentFrameAndMarkUnsaved(label);
      currentPoints = [];
      hoverNearFirst = false;
      warningMessage = "";
      redrawCanvas();
    } else {
      // Add point with validations
      if (
        currentPoints.length > 0 &&
        distance(point, currentPoints[currentPoints.length - 1]) <
          DISTANCE_THRESHOLD
      ) {
        warningMessage = "Point too close to previous! Duplicate ignored.";
        setTimeout(() => (warningMessage = ""), 3000);
        return;
      }
      if (wouldIntersect(point)) {
        warningMessage = "Would create self-intersection! Point ignored.";
        setTimeout(() => (warningMessage = ""), 3000);
        return;
      }
      currentPoints.push(point);
      redrawCanvas();
    }
  }

  function handleMouseMove(event: MouseEvent) {
    if (!isDrawing || currentPoints.length < 3) {
      hoverNearFirst = false;
      return;
    }
    const point = getCanvasPoint(event);
    hoverNearFirst = distance(point, currentPoints[0]) < DISTANCE_THRESHOLD;
    redrawCanvas();
  }

  function handleStartDrawing() {
    startDrawing();
    currentPoints = [];
    warningMessage = "";
  }

  function handleCancelDrawing() {
    stopDrawing();
    currentPoints = [];
    hoverNearFirst = false;
    warningMessage = "";
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
  {#if !fullscreen}
  <div class="flex items-center gap-4">
    <div class="flex flex-col gap-2">
      <label for="class-select" class="text-sm font-medium">Class:</label>
      <select
        id="class-select"
        value={selectedClassId}
        onchange={(e) => setSelectedClassId(Number((e.target as HTMLSelectElement).value))}
        class="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {#each CLASS_NAMES as className, index}
          <option value={index}>{className}</option>
        {/each}
      </select>
    </div>
  </div>
  {/if}

  <div class="flex items-center gap-4">
    <div class="flex gap-2">
      <button
        onclick={handleStartDrawing}
        disabled={isDrawing}
        class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Start Drawing
      </button>

      <button
        onclick={handleCancelDrawing}
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
      onmousemove={handleMouseMove}
      class="border border-gray-300 rounded-lg cursor-crosshair max-w-full"
    ></canvas>
  </div>

  <div class="text-sm text-gray-600">
    {#if warningMessage}
      <p class="text-red-600">{warningMessage}</p>
    {:else if isDrawing}
      <p>
        Click to add points ({currentPoints.length}). Hover and click first
        point to close after 3+ points.
      </p>
    {:else}
      <p>Select a class and click "Start Drawing" to begin labeling</p>
    {/if}
  </div>
</div>
