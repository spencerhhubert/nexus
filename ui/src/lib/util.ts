export function toTitleCase(phrase: string): string {
  return phrase
    .toLowerCase()
    .split(' ')
    .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
