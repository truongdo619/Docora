// src/types/CollData.ts
export interface EntityType  { type: string; labels: string[]; bgColor: string; borderColor: string; }
export interface RelationType { type: string; dashArray: string; color: string; labels: string[]; args: { role: string; targets: string[] }[]; }
export interface EventType   { type: string; labels: string[]; bgColor: string; borderColor: string; arcs?: { type: string; labels: string[]; color: string }[]; }

export interface CollData {
  entity_types:   EntityType[];
  relation_types: RelationType[];
  event_types:    EventType[];
}

// src/collData.ts
import rawCollData from '../../settings.json' assert { type: 'json' };
// without `assert` you can also write:  import rawCollData from './settings.json';

export const collData: CollData = rawCollData as CollData;