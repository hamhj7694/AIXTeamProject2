import type { BankCaseWorkspace, CaseEvent, ContextFeature, WorkspaceCase } from '../api/cases.ts';
import type { CaseEntity, CaseEntityState } from './caseDelta.ts';

export function workspaceEntityState(workspace: BankCaseWorkspace): CaseEntityState {
  const entities: Record<string, CaseEntity> = {
    [workspace.case.id]: { entity_id: workspace.case.id, version: workspace.case.version, data: workspace.case as unknown as Record<string, unknown> },
  };
  for (const participant of workspace.participants) {
    if (typeof participant.id === 'string' && typeof participant.version === 'number') {
      entities[participant.id] = { entity_id: participant.id, version: participant.version, data: participant };
    }
  }
  for (const event of workspace.events) {
    entities[event.id] = { entity_id: event.id, version: event.case_revision, data: event as unknown as Record<string, unknown> };
  }
  for (const item of [...(workspace.tasks ?? []), ...(workspace.suggestions ?? [])]) {
    entities[item.id] = { entity_id: item.id, version: item.version, data: { ...item } };
  }
  return { revision: workspace.case.revision, fingerprint: workspace.case.fingerprint, entities };
}

export function caseFromEntityState(state: CaseEntityState): WorkspaceCase | null {
  for (const entity of Object.values(state.entities)) {
    if (entity.data.id === entity.entity_id && typeof entity.data.fingerprint === 'string') return entity.data as unknown as WorkspaceCase;
  }
  return null;
}

export function timelineFromEntityState(state: CaseEntityState): CaseEvent[] {
  return Object.values(state.entities)
    .map((entity) => entity.data)
    .filter((item): item is Record<string, unknown> => typeof item.entity_type === 'string' && typeof item.case_revision === 'number')
    .map((item) => item as unknown as CaseEvent)
    .sort((left, right) => left.case_revision - right.case_revision || left.created_at.localeCompare(right.created_at));
}

export interface RiskSummary { score: number | null; classification: string | null; }

export function latestRisk(contextFeatures: ContextFeature[], timeline: CaseEvent[]): RiskSummary {
  const latestFeature = contextFeatures[0]?.payload.model_result as Record<string, unknown> | undefined;
  if (typeof latestFeature === 'object' && latestFeature !== null &&
      typeof latestFeature.final_risk_score === 'number' && typeof latestFeature.label === 'string') {
    return { score: latestFeature.final_risk_score, classification: latestFeature.label };
  }
  const update = [...timeline].reverse().find((event) => event.entity_type === 'CONTEXT_FEATURE' &&
    typeof event.payload.risk_score === 'number' && typeof event.payload.classification === 'string');
  return update ? { score: update.payload.risk_score as number, classification: update.payload.classification as string } :
    { score: null, classification: null };
}
