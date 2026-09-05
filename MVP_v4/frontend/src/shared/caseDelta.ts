export interface CaseEntity { entity_id: string; version: number; data: Record<string, unknown>; }
export interface CaseDelta { revision: number; fingerprint: string; unchanged: boolean; upserts: CaseEntity[]; deleted_entity_ids: string[]; }
export interface CaseEntityState { revision: number; fingerprint: string; entities: Record<string, CaseEntity>; }

/** Applies only newer server entities. Local draft IDs retain their object and editing state. */
export function mergeCaseDelta(current: CaseEntityState, delta: CaseDelta, localEditIds: ReadonlySet<string>): CaseEntityState {
  if (delta.unchanged || delta.revision <= current.revision) return current;
  const entities = { ...current.entities };
  for (const id of delta.deleted_entity_ids) if (!localEditIds.has(id)) delete entities[id];
  for (const entity of delta.upserts) if (!localEditIds.has(entity.entity_id)) entities[entity.entity_id] = entity;
  return { revision: delta.revision, fingerprint: delta.fingerprint, entities };
}
