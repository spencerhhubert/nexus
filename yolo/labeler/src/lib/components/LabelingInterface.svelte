<script lang="ts">
  import PolygonDrawer from './PolygonDrawer.svelte';
  import { getCurrentFrame, removeLabelFromCurrentFrame, getCurrentFrameIndex, markFrameAsSaved } from '../stores/labeling.svelte';
  import { CLASS_COLORS } from '../constants.js';

  let currentFrame = $derived(getCurrentFrame());
  let selectedLabelIndices = $state<number[]>([]);

  function toggleLabelSelection(index: number) {
    if (selectedLabelIndices.includes(index)) {
      selectedLabelIndices = selectedLabelIndices.filter(i => i !== index);
    } else {
      selectedLabelIndices = [...selectedLabelIndices, index];
    }
  }

  function removeLabelAtIndex(index: number) {
    // Remove from selection first
    selectedLabelIndices = selectedLabelIndices.filter(i => i !== index);
    // Adjust indices for labels that come after the removed one
    selectedLabelIndices = selectedLabelIndices.map(i => i > index ? i - 1 : i);
    // Remove the label
    removeLabelFromCurrentFrame(index);
  }

  // Clear selection when frame changes
  $effect(() => {
    selectedLabelIndices = [];
  });

  async function saveCurrentFrame() {
    const frame = getCurrentFrame();
    const frameIndex = getCurrentFrameIndex();

    if (!frame || frameIndex === null) return;

    try {
      const response = await fetch('/api/save-label', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          imageData: frame.imageData,
          labels: frame.labels,
          timestamp: frame.timestamp
        })
      });

      const result = await response.json();
      if (result.success) {
        markFrameAsSaved(frameIndex, result.timestamp);
        alert(`Frame saved successfully`);
      } else {
        alert('Failed to save frame');
      }
    } catch (error) {
      console.error('Error saving frame:', error);
      alert('Error saving frame');
    }
  }
</script>

{#if currentFrame}
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">Labeling Frame</h3>
      <div class="flex items-center gap-4">
        <div class="text-sm text-gray-500">
          {currentFrame.labels.length} label{currentFrame.labels.length !== 1 ? 's' : ''}
        </div>
        {#if currentFrame.labels.length > 0}
          <button
            onclick={saveCurrentFrame}
            class="px-4 py-2 {currentFrame.isSaved ? 'bg-green-100 text-green-800' : 'bg-blue-600 text-white hover:bg-blue-700'} rounded-md transition-colors"
            disabled={currentFrame.isSaved}
          >
            {currentFrame.isSaved ? '✓ Saved' : 'Save Frame'}
          </button>
        {/if}
      </div>
    </div>

    <PolygonDrawer
      imageData={currentFrame.imageData}
      labels={currentFrame.labels}
      selectedLabelIndices={selectedLabelIndices}
    />

    {#if currentFrame.labels.length > 0}
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h4 class="font-medium">Current Labels:</h4>
          {#if selectedLabelIndices.length > 0}
            <button
              onclick={() => selectedLabelIndices = []}
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear Selection ({selectedLabelIndices.length})
            </button>
          {/if}
        </div>
        {#if selectedLabelIndices.length === 0}
          <p class="text-sm text-gray-500">Click labels to highlight them on the image</p>
        {/if}
        <div class="space-y-2">
          {#each currentFrame.labels as label, index}
            <div class="flex items-center justify-between p-3 border rounded-lg transition-colors {selectedLabelIndices.includes(index) ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'}">
              <button
                onclick={() => toggleLabelSelection(index)}
                class="flex items-center gap-3 flex-1 text-left"
              >
                <div
                  class="w-4 h-4 rounded {selectedLabelIndices.includes(index) ? 'ring-2 ring-blue-500' : ''}"
                  style="background-color: {CLASS_COLORS[label.className as keyof typeof CLASS_COLORS]}"
                ></div>
                <span class="font-medium">{label.className}</span>
                <span class="text-sm text-gray-500">
                  ({label.points.length} points)
                </span>
                {#if selectedLabelIndices.includes(index)}
                  <span class="text-xs text-blue-600 font-medium">SELECTED</span>
                {/if}
              </button>
              <button
                onclick={() => removeLabelAtIndex(index)}
                class="px-3 py-1 text-red-600 hover:bg-red-50 rounded ml-2"
              >
                Remove
              </button>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{:else}
  <div class="text-center py-12">
    <p class="text-gray-500">Select a frame to start labeling</p>
  </div>
{/if}