<script lang="ts">
  import type { KnownObject } from '../types/websocket';
  import { getBricklinkPartInfo } from '$lib/api-client';
  import KnownObjectLoadingState from './KnownObjectLoadingState.svelte';


  interface Props {
    knownObject: KnownObject;
  }

  let { knownObject }: Props = $props();

  let bricklinkData = $state(null);
  let fetchingData: boolean = $state(false);
  let fetchError: boolean = $state(false);
  let lastFetchedPartId: string | null = $state(null);
  let retryCount: number = $state(0);
  let lastRetryTime: number = $state(0);
  let processedImageUrl: string | null = $state(null);

  function decodeHtmlEntities(str: string): string {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = str;
    return textarea.value;
  }

  function removeWhiteBackground(imageUrl: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';

      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        if (!ctx) {
          reject(new Error('Could not get canvas context'));
          return;
        }

        canvas.width = img.width;
        canvas.height = img.height;

        ctx.drawImage(img, 0, 0);

        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;

        // Remove white pixels (make them transparent)
        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];

          // Check if pixel is close to white
          if (r > 240 && g > 240 && b > 240) {
            data[i + 3] = 0; // Set alpha to 0 (transparent)
          }
        }

        ctx.putImageData(imageData, 0, 0);
        resolve(canvas.toDataURL('image/png'));
      };

      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = `https:${imageUrl}`;
    });
  }

  async function fetchBricklinkData(partId: string) {
    if (fetchingData) return;

    fetchingData = true;
    try {
      const data = await getBricklinkPartInfo(partId);
      bricklinkData = data;
      lastFetchedPartId = partId;
      retryCount = 0;
      fetchError = false;

      // Process the thumbnail to remove white background
      if (data.thumbnail_url) {
        try {
          const processedUrl = await removeWhiteBackground(data.thumbnail_url);
          processedImageUrl = processedUrl;
        } catch (error) {
          console.error('Failed to process thumbnail:', error);
          processedImageUrl = null;
        }
      }
    } catch (error) {
      console.error('Failed to fetch BrickLink data:', error);
      retryCount++;
      lastRetryTime = Date.now();
      if (retryCount >= 3) {
        fetchError = true;
      }
    } finally {
      fetchingData = false;
    }
  }

  $effect(() => {
    if (knownObject.classification_id && !bricklinkData && !fetchingData && !fetchError) {
      // Reset retry logic for new part
      if (lastFetchedPartId !== knownObject.classification_id) {
        retryCount = 0;
        fetchError = false;
        lastRetryTime = 0;
        lastFetchedPartId = null;
      }

      // Check if we should attempt/retry
      const shouldAttempt = lastFetchedPartId !== knownObject.classification_id;
      const shouldRetry = retryCount > 0 &&
                         retryCount < 3 &&
                         (Date.now() - lastRetryTime) >= 1000;

      if (shouldAttempt || shouldRetry) {
        fetchBricklinkData(knownObject.classification_id);
      }
    }
  });
</script>

<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 mb-3 overflow-hidden">
  {#if !knownObject.classification_id}
    <!-- Classifying state -->
    <KnownObjectLoadingState {knownObject} />
  {:else if bricklinkData}
    <!-- Classified state -->
    <div class="p-4 flex items-start gap-4">
      <div class="flex-shrink-0">
        <img
          src="{processedImageUrl || `https:${bricklinkData.thumbnail_url}`}"
          alt="{bricklinkData.name}"
          class="w-24 h-24 object-contain border border-gray-300 dark:border-gray-600"
        />
      </div>

      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
          {decodeHtmlEntities(bricklinkData.name)}
        </h3>

        <div class="space-y-1 text-xs text-gray-600 dark:text-gray-400">
          <div>
            {bricklinkData.no}
          </div>
        </div>
      </div>
    </div>
  {:else if fetchError}
    <!-- Error state -->
    <div class="p-4">
      <div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
        {knownObject.classification_id}
      </div>
      <div class="text-xs text-red-500 dark:text-red-400">
        Failed to load part info
      </div>
    </div>
  {:else}
    <!-- Loading BrickLink data -->
    <div class="p-4">
      <div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
        {knownObject.classification_id}
      </div>
      <div class="text-xs text-blue-500 dark:text-blue-400">
        Loading part info...
      </div>
    </div>
  {/if}
</div>
