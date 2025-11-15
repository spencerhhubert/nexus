export const CLASS_NAMES = [
  'object',
  'first_feeder',
  'second_feeder',
  'main_conveyor',
  'feeder_conveyor'
] as const;

export type ClassName = typeof CLASS_NAMES[number];

export const CLASS_COLORS: Record<ClassName, string> = {
  object: '#ef4444',
  first_feeder: '#3b82f6',
  second_feeder: '#10b981',
  main_conveyor: '#f59e0b',
  feeder_conveyor: '#8b5cf6'
};