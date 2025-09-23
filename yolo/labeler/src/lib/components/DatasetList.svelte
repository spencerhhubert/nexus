<script lang="ts">
  import { onMount } from 'svelte';

  interface Dataset {
    filename: string;
    timestamp: string;
    imagePath: string;
    labelPath: string;
    labelCount: number;
    fileSize: number;
    lastModified: string;
  }

  interface Props {
    selectedDataset: Dataset | null;
    onDatasetSelect: (dataset: Dataset) => void;
  }

  let { selectedDataset, onDatasetSelect }: Props = $props();
  let datasets: Dataset[] = $state([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    try {
      const response = await fetch('/api/datasets');
      const data = await response.json();

      if (data.error) {
        error = data.error;
      } else {
        datasets = data.datasets;
      }
    } catch (err) {
      error = 'Failed to load datasets';
      console.error('Error loading datasets:', err);
    } finally {
      loading = false;
    }
  });

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }
</script>

<div class="h-full flex flex-col">
  <div class="mb-4">
    <h3 class="text-lg font-semibold text-gray-900">Saved Datasets</h3>
    <p class="text-sm text-gray-500">
      {datasets.length} saved image{datasets.length !== 1 ? 's' : ''}
    </p>
  </div>

  {#if loading}
    <div class="flex-1 flex items-center justify-center">
      <div class="text-gray-500">Loading datasets...</div>
    </div>
  {:else if error}
    <div class="flex-1 flex items-center justify-center">
      <div class="text-red-500">{error}</div>
    </div>
  {:else if datasets.length === 0}
    <div class="flex-1 flex items-center justify-center">
      <div class="text-center text-gray-500">
        <p>No datasets found</p>
        <p class="text-sm mt-1">Create some labels first!</p>
      </div>
    </div>
  {:else}
    <div class="flex-1 overflow-y-auto space-y-2">
      {#each datasets as dataset}
        <button
          onclick={() => onDatasetSelect(dataset)}
          class="w-full text-left p-3 rounded-lg border transition-colors {
            selectedDataset?.filename === dataset.filename
              ? 'bg-blue-50 border-blue-300'
              : 'bg-white border-gray-200 hover:bg-gray-50'
          }"
        >
          <div class="font-medium text-sm text-gray-900 mb-1">
            {dataset.filename}
          </div>
          <div class="flex items-center justify-between text-xs text-gray-500">
            <span>{dataset.labelCount} label{dataset.labelCount !== 1 ? 's' : ''}</span>
            <span>{formatFileSize(dataset.fileSize)}</span>
          </div>
          <div class="text-xs text-gray-400 mt-1">
            {formatDate(dataset.lastModified)}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>