<script lang="ts">
  interface Props {
    id: string;
    label: string;
    checked: boolean;
  }

  let { id, label, checked = $bindable() }: Props = $props();
</script>

<div class="flex items-center">
  <input
    {id}
    type="checkbox"
    bind:checked
    class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
  />
  <label for={id} class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
    {label}
  </label>
</div>