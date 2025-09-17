<script lang="ts">
  interface Props {
    lifecycleStage: string;
    sortingState: string;
  }

  let { lifecycleStage, sortingState }: Props = $props();
</script>

<div class="bg-white dark:bg-gray-800 p-6 border border-gray-200 dark:border-gray-700">
  <h2 class="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">System Status</h2>
  <div class="flex items-center gap-4 mb-4">
    <span class="font-medium text-gray-700 dark:text-gray-300">Lifecycle Stage:</span>
    <span class="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-800">
      {lifecycleStage}
    </span>
  </div>
  <div class="flex items-center gap-4 mb-4">
    <span class="font-medium text-gray-700 dark:text-gray-300">Sorting State:</span>
    <span class="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800">
      {sortingState}
    </span>
  </div>
</div>