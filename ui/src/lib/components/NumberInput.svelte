<script lang="ts">
  interface Props {
    id: string;
    label: string;
    value: number;
    min?: number;
    max?: number;
  }

  let { id, label, value = $bindable(), min, max }: Props = $props();
</script>

<div>
  <label for={id} class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
    {label}
  </label>
  <input
    {id}
    type="number"
    bind:value
    {min}
    {max}
    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
  />
</div>