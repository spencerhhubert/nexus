<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { getBinState, getBricklinkCategoryInfo, getBricklinkCategories, updateBinState } from '$lib/api-client';
  import type { BinStateUpdateMessage, WebSocketMessage } from '$lib/types/websocket';
  import type { components } from '$lib/api-types';
  import { Trash2, Edit, AlertTriangle } from 'lucide-svelte';
  import SearchableDropdown from './SearchableDropdown.svelte';
  import Tooltip from './Tooltip.svelte';

  type BinState = components['schemas']['BinState'];
  type BricklinkCategoryData = components['schemas']['BricklinkCategoryData'];

  let bin_state: BinState | null = $state(null);
  let category_names: Record<string, string> = $state({});
  let websocket: WebSocket | null = null;
  let all_categories: BricklinkCategoryData[] = $state([]);
  let editing_bin: string | null = $state(null);
  let hovered_bin: string | null = $state(null);

  const MISC_CATEGORY = 'misc';
  const FALLBACK_CATEGORY = 'fallback';

  async function loadBinState() {
    try {
      bin_state = await getBinState();
      await loadCategoryNames();
    } catch (error) {
      console.error('Failed to load bin state:', error);
    }
  }

  async function loadCategories() {
    try {
      all_categories = await getBricklinkCategories();
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  }

  async function loadCategoryNames() {
    if (!bin_state) return;

    const new_category_names: Record<string, string> = {};

    for (const category_id of Object.values(bin_state.bin_contents)) {
      if (category_id && !category_names[category_id] &&
          category_id !== MISC_CATEGORY &&
          category_id !== FALLBACK_CATEGORY) {
        try {
          const category_info = await getBricklinkCategoryInfo(parseInt(category_id));
          new_category_names[category_id] = category_info.category_name;
        } catch (error) {
          console.error(`Failed to load category ${category_id}:`, error);
          new_category_names[category_id] = category_id;
        }
      }
    }

    category_names = { ...category_names, ...new_category_names };
  }

  function connectWebSocket() {
    websocket = new WebSocket('ws://localhost:8000/ws');

    websocket.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        if (message.type === 'bin_state_update') {
          handleBinStateUpdate(message as BinStateUpdateMessage);
        }
      } catch (error) {
        console.error('Failed to parse websocket message:', error);
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      setTimeout(connectWebSocket, 5000);
    };
  }

  async function handleBinStateUpdate(message: BinStateUpdateMessage) {
    bin_state = {
      bin_contents: message.bin_contents,
      timestamp: message.timestamp
    };
    await loadCategoryNames();
  }

  function getBinDisplayName(category_id: string | null): string {
    if (!category_id) return 'Empty';
    if (category_id === MISC_CATEGORY) return 'Misc';
    if (category_id === FALLBACK_CATEGORY) return 'Fallback';
    return category_names[category_id] || 'Occupied';
  }

  function getBinClasses(category_id: string | null): string {
    if (!category_id) {
      return 'border-gray-200 dark:border-gray-600 bg-gray-100 dark:bg-gray-700';
    }
    if (category_id === MISC_CATEGORY) {
      return 'border-blue-200 dark:border-blue-800 bg-blue-100 dark:bg-blue-900';
    }
    if (category_id === FALLBACK_CATEGORY) {
      return 'border-yellow-200 dark:border-yellow-800 bg-yellow-100 dark:bg-yellow-900';
    }
    return 'border-green-200 dark:border-green-800 bg-green-100 dark:bg-green-900';
  }

  async function clearBin(module_idx: number, bin_idx: number) {
    try {
      await updateBinState(
        { distribution_module_idx: module_idx, bin_idx: bin_idx },
        null
      );
    } catch (error) {
      console.error('Failed to clear bin:', error);
    }
  }

  function editBin(bin_key: string) {
    editing_bin = bin_key;
  }

  function cancelEdit() {
    editing_bin = null;
  }

  async function selectCategory(item: { id: string; name: string }) {
    if (!editing_bin) return;

    const { module_idx, bin_idx } = parseBinCoordinates(editing_bin);
    try {
      await updateBinState(
        { distribution_module_idx: module_idx, bin_idx: bin_idx },
        item.id
      );
      editing_bin = null;
    } catch (error) {
      console.error('Failed to update bin category:', error);
    }
  }

  function parseBinCoordinates(bin_key: string): { module_idx: number; bin_idx: number } {
    const [module_idx, bin_idx] = bin_key.split('_').map(Number);
    return { module_idx, bin_idx };
  }

  function groupBinsByModule(): Record<number, Array<{ key: string; bin_idx: number; category_id: string | null }>> {
    if (!bin_state) return {};

    const grouped: Record<number, Array<{ key: string; bin_idx: number; category_id: string | null }>> = {};

    for (const [bin_key, category_id] of Object.entries(bin_state.bin_contents)) {
      const { module_idx, bin_idx } = parseBinCoordinates(bin_key);

      if (!grouped[module_idx]) {
        grouped[module_idx] = [];
      }

      grouped[module_idx].push({ key: bin_key, bin_idx, category_id });
    }

    // Sort bins within each module by bin_idx
    for (const module_bins of Object.values(grouped)) {
      module_bins.sort((a, b) => a.bin_idx - b.bin_idx);
    }

    return grouped;
  }

  onMount(() => {
    loadBinState();
    loadCategories();
    connectWebSocket();
  });

  onDestroy(() => {
    if (websocket) {
      websocket.close();
    }
  });

  const grouped_bins = $derived(groupBinsByModule());

  const duplicate_categories = $derived.by(() => {
    if (!bin_state) return new Set<string>();

    const category_counts: Record<string, number> = {};
    for (const category_id of Object.values(bin_state.bin_contents)) {
      if (category_id) {
        category_counts[category_id] = (category_counts[category_id] || 0) + 1;
      }
    }

    return new Set(
      Object.entries(category_counts)
        .filter(([_, count]) => count > 1)
        .map(([category_id, _]) => category_id)
    );
  });

  const category_dropdown_items = $derived.by(() => [
    { id: MISC_CATEGORY, name: 'Misc' },
    { id: FALLBACK_CATEGORY, name: 'Fallback' },
    ...all_categories.map(cat => ({ id: cat.category_id.toString(), name: cat.category_name }))
  ]);
</script>

<div class="p-4">
  <h3 class="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">Bin State</h3>

  {#if bin_state}
    <div class="flex gap-4 items-start w-full">
      {#each Object.entries(grouped_bins).sort(([a], [b]) => Number(a) - Number(b)) as [module_idx, bins]}
        <div class="border border-gray-300 dark:border-gray-600 p-4 bg-white dark:bg-gray-700 flex-1">
          <h4 class="text-sm font-medium mb-2 text-gray-700 dark:text-gray-300">
            Module {Number(module_idx) + 1}
          </h4>
          <div class="flex flex-col gap-2">
            {#each bins as { key, bin_idx, category_id }}
              <div
                   role="button"
                   tabindex="0"
                   class="border-2 p-2 text-center text-xs min-h-[60px] flex flex-col justify-center relative {getBinClasses(category_id)}"
                   onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && e.preventDefault()}
                   onmouseenter={() => hovered_bin = key}
                   onmouseleave={() => hovered_bin = null}>
                <div class="font-semibold text-gray-700 dark:text-gray-200">{Number(module_idx) + 1},{bin_idx + 1}</div>
                <div class="text-[0.625rem] mt-1 text-gray-600 dark:text-gray-300">{getBinDisplayName(category_id)}</div>

                {#if category_id && duplicate_categories.has(category_id)}
                  <div class="absolute top-1 right-1">
                    <Tooltip text="Multiple bins have the same category">
                      {#snippet children()}
                        <AlertTriangle size={16} color="#f59e0b" />
                      {/snippet}
                    </Tooltip>
                  </div>
                {/if}

                {#if hovered_bin === key}
                  <div class="absolute top-1 left-1 flex gap-1">
                    <button class="action-icon trash" onclick={(e) => { e.stopPropagation(); clearBin(Number(module_idx), bin_idx); }} title="Clear bin">
                      <Trash2 size={16} />
                    </button>
                    <button class="action-icon edit" onclick={(e) => { e.stopPropagation(); editBin(key); }} title="Edit category">
                      <Edit size={16} />
                    </button>
                  </div>
                {/if}

                {#if editing_bin === key}
                  <div class="absolute top-full left-0 right-0 z-[1001] mt-1">
                    <SearchableDropdown
                      items={category_dropdown_items}
                      onSelect={selectCategory}
                      onClose={cancelEdit}
                      placeholder="Search categories..."
                    />
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="text-gray-500 dark:text-gray-400">Loading bin state...</div>
  {/if}
</div>

<style>
  .action-icon {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid #d1d5db;
    padding: 0.25rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .action-icon:hover {
    background: rgba(255, 255, 255, 1);
  }

  .action-icon.trash:hover {
    background: #fee2e2;
    border-color: #fca5a5;
    color: #dc2626;
  }

  .action-icon.edit:hover {
    background: #dbeafe;
    border-color: #93c5fd;
    color: #2563eb;
  }

  :global(.dark) .action-icon {
    background: rgba(55, 65, 81, 0.9);
    border-color: #4b5563;
    color: #f3f4f6;
  }

  :global(.dark) .action-icon:hover {
    background: rgba(55, 65, 81, 1);
  }

  :global(.dark) .action-icon.trash:hover {
    background: #7f1d1d;
    border-color: #dc2626;
    color: #fca5a5;
  }

  :global(.dark) .action-icon.edit:hover {
    background: #1e3a8a;
    border-color: #2563eb;
    color: #93c5fd;
  }
</style>