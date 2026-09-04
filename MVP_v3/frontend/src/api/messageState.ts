import type { CaseMessage } from './types';

const sameLogicalMessage = (left: CaseMessage, right: CaseMessage) => (
  left.message_id === right.message_id
  || Boolean(left.client_request_id && left.client_request_id === right.client_request_id)
);

export const upsertMessage = (messages: CaseMessage[], incoming: CaseMessage): CaseMessage[] => [
  ...messages.filter((message) => !sameLogicalMessage(message, incoming)),
  incoming,
];

export const removeMessage = (messages: CaseMessage[], target: CaseMessage): CaseMessage[] => (
  messages.filter((message) => !sameLogicalMessage(message, target))
);

/**
 * Preserve locally submitted messages while a slower polling response is
 * replacing the server bundle. The request id reconciles the optimistic row
 * with the committed MySQL row without relying on timestamps.
 */
export const mergePendingMessages = (
  serverMessages: CaseMessage[],
  pendingMessages: Iterable<CaseMessage>,
): CaseMessage[] => {
  const ids = new Set(serverMessages.map((message) => message.message_id));
  const requestIds = new Set(
    serverMessages
      .map((message) => message.client_request_id)
      .filter((value): value is string => Boolean(value)),
  );
  const pending = Array.from(pendingMessages).filter((message) => (
    !ids.has(message.message_id)
    && (!message.client_request_id || !requestIds.has(message.client_request_id))
  ));
  return [...serverMessages, ...pending];
};
