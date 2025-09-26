<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  interface Item {
    id: string;
    name: string;
  }

  interface Props {
    items: Item[];
    onSelect: (item: Item) => void;
    onClose?: () => void;
    placeholder?: string;
  }

  let { items, onSelect, onClose, placeholder = 'Search...' }: Props = $props();

  let search_query = $state('');
  let selected_index = $state(-1);
  let dropdown_element: HTMLDivElement | null = $state(null);
  let input_element: HTMLInputElement | null = $state(null);

  const filtered_items: Item[] = $derived.by(() => {
    if (!search_query.trim()) return items;
    return items.filter(item =>
      item.name.toLowerCase().includes(search_query.toLowerCase())
    );
  });

  function selectItem(item: Item) {
    onSelect(item);
    if (onClose) onClose();
  }

  function handleKeydown(event: KeyboardEvent) {
    const max_index = filtered_items.length - 1;

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        selected_index = selected_index < max_index ? selected_index + 1 : 0;
        break;
      case 'ArrowUp':
        event.preventDefault();
        selected_index = selected_index > 0 ? selected_index - 1 : max_index;
        break;
      case 'Enter':
        event.preventDefault();
        if (selected_index >= 0 && filtered_items[selected_index]) {
          selectItem(filtered_items[selected_index]);
        }
        break;
      case 'Escape':
        event.preventDefault();
        if (onClose) onClose();
        break;
    }
  }

  function handleClickOutside(event: MouseEvent) {
    if (dropdown_element && !dropdown_element.contains(event.target as Node)) {
      if (onClose) onClose();
    }
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    if (input_element) {
      input_element.focus();
    }
  });

  onDestroy(() => {
    document.removeEventListener('click', handleClickOutside);
  });
</script>

<div bind:this={dropdown_element} class="searchable-dropdown">
  <input
    bind:this={input_element}
    bind:value={search_query}
    onkeydown={handleKeydown}
    {placeholder}
    class="search-input"
    role="combobox"
    aria-expanded="true"
    aria-autocomplete="list"
    aria-controls="dropdown-list"
  />

  {#if filtered_items.length > 0}
    <div class="dropdown-list" id="dropdown-list" role="listbox">
      {#each filtered_items as item, index}
        <div
          role="option"
          class="dropdown-item"
          class:selected={index === selected_index}
          onclick={() => selectItem(item)}
          onkeydown={(e) => e.key === 'Enter' && selectItem(item)}
          onmouseenter={() => selected_index = index}
          tabindex="-1"
          aria-selected={index === selected_index}
        >
          {item.name}
        </div>
      {/each}
    </div>
  {:else}
    <div class="no-results">No results found</div>
  {/if}
</div>

<style>
  .searchable-dropdown {
    position: relative;
    background: white;
    border: 1px solid #d1d5db;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    min-width: 200px;
    z-index: 1000;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem;
    border: none;
    outline: none;
    font-size: 0.875rem;
  }

  .dropdown-list {
    max-height: 200px;
    overflow-y: auto;
    border-top: 1px solid #e5e7eb;
  }

  .dropdown-item {
    padding: 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
    border-bottom: 1px solid #f3f4f6;
  }

  .dropdown-item:hover,
  .dropdown-item.selected {
    background-color: #f3f4f6;
  }

  .dropdown-item:last-child {
    border-bottom: none;
  }

  .no-results {
    padding: 0.5rem;
    font-size: 0.875rem;
    color: #6b7280;
    text-align: center;
    border-top: 1px solid #e5e7eb;
  }

  :global(.dark) .searchable-dropdown {
    background: #374151;
    border-color: #4b5563;
  }

  :global(.dark) .search-input {
    background: #374151;
    color: #f3f4f6;
  }

  :global(.dark) .dropdown-list {
    border-top-color: #4b5563;
  }

  :global(.dark) .dropdown-item {
    color: #f3f4f6;
    border-bottom-color: #4b5563;
  }

  :global(.dark) .dropdown-item:hover,
  :global(.dark) .dropdown-item.selected {
    background-color: #4b5563;
  }

  :global(.dark) .no-results {
    color: #9ca3af;
    border-top-color: #4b5563;
  }
</style>