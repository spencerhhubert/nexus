<script lang="ts">
  import type { KnownObject } from '../types/websocket';
  import KnownObjectCard from './KnownObjectCard.svelte';
  import { getPageState } from '../stores/page-state.svelte';

  const pageState = getPageState();

  let knownObjectsList: KnownObject[] = $derived(
    Array.from(pageState.state.knownObjects.values()).reverse()
  );
</script>

<div class="h-full flex flex-col">
  <div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
    <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Classifications</h2>
    <p class="text-sm text-gray-500 dark:text-gray-400">{knownObjectsList.length} object{knownObjectsList.length !== 1 ? 's' : ''}</p>
  </div>

  <div class="flex-1 overflow-y-auto p-4">
    {#if knownObjectsList.length === 0}
      <div class="text-center text-gray-500 dark:text-gray-400 mt-8">
        <p class="text-sm">No objects detected yet</p>
        <p class="text-xs mt-1">Objects will appear here as they are detected</p>
      </div>
    {:else}
      {#each knownObjectsList as knownObject (knownObject.uuid)}
        <KnownObjectCard {knownObject} />
      {/each}
    {/if}
  </div>
</div>
