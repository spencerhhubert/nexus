<script lang="ts">
  import { getCapturedFrames, getCurrentFrameIndex, selectFrame, getCurrentFrame, markFrameAsSaved } from '../stores/labeling.svelte';

  let capturedFrames = $derived(getCapturedFrames());
  let currentFrameIndex = $derived(getCurrentFrameIndex());
  let unsavedFrames = $derived(capturedFrames.filter(frame => !frame.isSaved));

  async function saveFrame(frame: any, frameIndex: number) {
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
        return true;
      } else {
        console.error('Failed to save frame:', result.error);
        return false;
      }
    } catch (error) {
      console.error('Error saving frame:', error);
      return false;
    }
  }

  async function saveAllUnsavedFrames() {
    let saved = 0;
    let failed = 0;

    for (let i = 0; i < capturedFrames.length; i++) {
      const frame = capturedFrames[i];
      if (!frame.isSaved && frame.labels.length > 0) {
        const success = await saveFrame(frame, i);
        if (success) {
          saved++;
        } else {
          failed++;
        }
      }
    }

    if (failed > 0) {
      alert(`Saved ${saved} frames, ${failed} failed`);
    } else {
      alert(`Successfully saved ${saved} frames`);
    }
  }
</script>

<div class="space-y-4">
  <div class="flex items-center justify-between">
    <h3 class="text-lg font-semibold">Captured Frames ({capturedFrames.length})</h3>
    {#if unsavedFrames.length > 0}
      <button
        onclick={saveAllUnsavedFrames}
        class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
      >
        Save All Unsaved ({unsavedFrames.length})
      </button>
    {/if}
  </div>

  {#if capturedFrames.length === 0}
    <p class="text-gray-500 text-center py-8">No frames captured yet</p>
  {:else}
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {#each capturedFrames as frame, index}
        <button
          class="border rounded-lg overflow-hidden cursor-pointer hover:shadow-lg transition-shadow text-left w-full relative {currentFrameIndex === index ? 'ring-2 ring-blue-500' : ''}"
          onclick={() => selectFrame(index)}
        >
          <img
            src={frame.imageData}
            alt="Frame {index + 1}"
            class="w-full h-32 object-cover"
          />

          <!-- Save status badge -->
          {#if frame.isSaved}
            <div class="absolute top-2 right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full">
              ✓ Saved
            </div>
          {:else if frame.labels.length > 0}
            <div class="absolute top-2 right-2 bg-orange-500 text-white text-xs px-2 py-1 rounded-full">
              Unsaved
            </div>
          {/if}

          <div class="p-2">
            <p class="text-sm font-medium">Frame {index + 1}</p>
            <p class="text-xs text-gray-500">
              {frame.labels.length} label{frame.labels.length !== 1 ? 's' : ''}
            </p>
            <p class="text-xs text-gray-400">
              {new Date(frame.timestamp).toLocaleTimeString()}
            </p>
            {#if frame.isSaved && frame.savedTimestamp}
              <p class="text-xs text-green-600 font-medium">
                Saved: {new Date(frame.savedTimestamp).toLocaleTimeString()}
              </p>
            {/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>