<script lang="ts">
  interface Props {
    text: string;
    variant?: 'blue' | 'green' | 'yellow' | 'purple' | 'gray';
  }

  let { text, variant = 'blue' }: Props = $props();

  const variants = {
    blue: 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-800',
    green: 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border-green-200 dark:border-green-800',
    yellow: 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800',
    purple: 'bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 border-purple-200 dark:border-purple-800',
    gray: 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border-gray-200 dark:border-gray-600'
  };
</script>

<span class="px-3 py-1 border {variants[variant]} text-sm">
  {text}
</span>