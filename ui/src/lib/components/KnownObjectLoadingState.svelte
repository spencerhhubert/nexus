<script lang="ts">
  import type { KnownObject } from '../types/websocket';

  interface Props {
    knownObject: KnownObject;
  }

  let { knownObject }: Props = $props();
</script>

<div class="relative w-full h-20 overflow-hidden">
  <!-- Classifying text overlay -->
  <div class="absolute inset-0 z-10 flex items-center justify-center">
    <div class="bg-black bg-opacity-50 px-3 py-1 text-white text-sm font-medium">
      Classifying...
    </div>
  </div>

  <!-- Row of pulsing images -->
  <div class="flex gap-1 h-full animate-pulse">
    {#if knownObject.image}
      <!-- Show multiple copies of the same image to create a row effect -->
      {#each Array(8) as _, i}
        <div class="flex-shrink-0 h-full w-16">
          <img
            src="data:image/jpeg;base64,{knownObject.image}"
            alt="Detected object frame {i + 1}"
            class="w-full h-full object-cover grayscale-[0.8] opacity-60 animate-pulse"
            style="animation-delay: {i * 0.1}s;"
          />
        </div>
      {/each}
    {:else}
      <!-- Fallback placeholder boxes if no image -->
      {#each Array(8) as _, i}
        <div
          class="flex-shrink-0 h-full w-16 bg-gray-300 dark:bg-gray-600 opacity-60 animate-pulse"
          style="animation-delay: {i * 0.1}s;"
        ></div>
      {/each}
    {/if}
  </div>
</div>
