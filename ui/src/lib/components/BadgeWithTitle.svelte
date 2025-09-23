<script lang="ts">
  import StatusBadge from './StatusBadge.svelte';

  interface Props {
    title: string;
    text: string;
    variant?: 'blue' | 'green' | 'yellow' | 'purple' | 'gray';
  }

  let { title, text, variant = 'blue' }: Props = $props();
</script>

<div>
  <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">{title}</div>
  <StatusBadge text={text} variant={variant} />
</div>