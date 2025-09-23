<script lang="ts">
  import DatasetList from './DatasetList.svelte';
  import DatasetViewer from './DatasetViewer.svelte';

  interface Dataset {
    filename: string;
    timestamp: string;
    imagePath: string;
    labelPath: string;
    labelCount: number;
    fileSize: number;
    lastModified: string;
  }

  let selectedDataset: Dataset | null = $state(null);

  function handleDatasetSelect(dataset: Dataset) {
    selectedDataset = dataset;
  }
</script>

<div class="flex gap-8" style="height: 800px;">
  <div class="w-1/3">
    <div class="bg-white rounded-lg shadow-md p-6" style="height: 800px;">
      <DatasetList {selectedDataset} onDatasetSelect={handleDatasetSelect} />
    </div>
  </div>

  <div class="flex-1">
    <div class="bg-white rounded-lg shadow-md p-6" style="height: 800px;">
      <DatasetViewer dataset={selectedDataset} />
    </div>
  </div>
</div>