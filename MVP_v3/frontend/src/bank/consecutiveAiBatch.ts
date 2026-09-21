export const BANK_AI_BATCH_DELAY_MS = 1200;

export type SavedAiMessage = { messageId: string; createdAt: string };

export type ConsecutiveAiMessage = {
  caseId: string;
  requesterUserId: string;
  channel?: 'TEAM' | 'CUSTOMER';
  messageId: string;
  content: string;
  saved?: Promise<SavedAiMessage | false>;
};

export type ReadyConsecutiveAiMessage = ConsecutiveAiMessage & SavedAiMessage;
export type AiBatchControl = {
  signal: AbortSignal;
  isSuperseded: () => boolean;
  supersedeIfPending: () => boolean;
};

type PendingGroup = { messages: ConsecutiveAiMessage[]; messageIds: Set<string> };
type ActiveGroup = {
  key: string;
  messages: ConsecutiveAiMessage[];
  controller: AbortController;
  superseded: boolean;
};
type TimerHandle = ReturnType<typeof setTimeout>;

const groupKey = (message: ConsecutiveAiMessage) => (
  `${message.caseId}\u0000${message.requesterUserId}\u0000${message.channel ?? 'TEAM'}`
);
const chronological = (left: ReadyConsecutiveAiMessage, right: ReadyConsecutiveAiMessage) => (
  left.createdAt.localeCompare(right.createdAt) || left.messageId.localeCompare(right.messageId)
);

export const buildConsecutiveAiPrompt = (messages: ReadyConsecutiveAiMessage[]) => {
  const request = messages.map((message, index) => `${index + 1}. ${message.content}`).join('\n');
  return `[현재 요청 - 연속 메시지]\n\n${request}\n\n현재 Shared Case 맥락만 바탕으로, 동료에게 답하듯 자연스럽게 업무를 지원해 주세요. 확인되지 않은 사실은 추정하지 말고, 고객에게 자동 전송하거나 지급정지·신고 등 외부 조치를 완료한 것처럼 표현하지 마세요.`;
};

export const buildConsecutiveCustomerAiPrompt = (messages: ReadyConsecutiveAiMessage[]) => {
  const request = messages.map((message, index) => `${index + 1}. ${message.content}`).join('\n');
  return `[현재 고객 메시지 - 연속 입력]\n\n${request}\n\n위 메시지를 시간순으로 함께 고려해 현재 질문에 안전하고 이해하기 쉽게 답해 주세요.`;
};

/**
 * 짧은 연속 입력을 묶고, 실행 중 새 MESSAGE가 저장되면 active 원문을 pending과
 * 다시 합친다. 저장 실패 입력은 generation을 무효화하거나 최종 batch에 넣지 않는다.
 */
export class ConsecutiveAiBatcher {
  private readonly groups = new Map<string, PendingGroup>();
  private timer: TimerHandle | null = null;
  private draining: Promise<void> | null = null;
  private active: ActiveGroup | null = null;
  private disposed = false;

  constructor(
    private readonly invoke: (messages: ReadyConsecutiveAiMessage[], control: AiBatchControl) => Promise<void>,
    private readonly delayMs = BANK_AI_BATCH_DELAY_MS,
  ) {}

  enqueue(message: ConsecutiveAiMessage) {
    if (this.disposed) return;
    const key = groupKey(message);
    if (this.active?.key === key && this.active.messages.some((item) => item.messageId === message.messageId)) return;
    const group = this.groups.get(key) ?? { messages: [], messageIds: new Set<string>() };
    if (group.messageIds.has(message.messageId)) {
      const index = group.messages.findIndex((item) => item.messageId === message.messageId);
      if (index >= 0) group.messages[index] = message;
      this.schedule();
      return;
    }
    group.messages.push(message);
    group.messageIds.add(message.messageId);
    this.groups.set(key, group);

    void (message.saved ?? Promise.resolve({ messageId: message.messageId, createdAt: new Date().toISOString() }))
      .then((saved) => { if (saved) this.supersedeActive(key); })
      .catch(() => undefined);
    if (!this.draining) this.schedule();
  }

  flushNow(): Promise<void> {
    if (this.disposed) return Promise.resolve();
    this.clearTimer();
    if (!this.draining) {
      this.draining = this.drain().finally(() => {
        this.draining = null;
        if (this.groups.size > 0 && !this.disposed) this.schedule();
      });
    }
    return this.draining;
  }

  waitForIdle(): Promise<void> { return this.draining ?? Promise.resolve(); }

  dispose() {
    this.disposed = true;
    this.clearTimer();
    this.active?.controller.abort();
    this.active = null;
    this.groups.clear();
  }

  private supersedeActive(key: string) {
    if (!this.active || this.active.key !== key || this.active.superseded) return;
    this.active.superseded = true;
    this.active.controller.abort();
  }

  private schedule() {
    this.clearTimer();
    this.timer = setTimeout(() => { void this.flushNow(); }, this.delayMs);
  }

  private clearTimer() {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }

  private requeueActive(active: ActiveGroup) {
    const pending = this.groups.get(active.key);
    const unique = new Map(
      [...active.messages, ...(pending?.messages ?? [])].map((message) => [message.messageId, message]),
    );
    this.groups.set(active.key, { messages: [...unique.values()], messageIds: new Set(unique.keys()) });
  }

  private async readyMessages(messages: ConsecutiveAiMessage[]) {
    const saved = await Promise.all(messages.map(async (message) => (
      message.saved ? await message.saved : { messageId: message.messageId, createdAt: new Date().toISOString() }
    )));
    return messages.flatMap((message, index) => {
      const result = saved[index];
      return result ? [{ ...message, ...result }] : [];
    }).sort(chronological);
  }

  private async drain() {
    while (!this.disposed && this.groups.size > 0) {
      const first = this.groups.entries().next().value as [string, PendingGroup] | undefined;
      if (!first) return;
      const [key, group] = first;
      this.groups.delete(key);
      const readyMessages = await this.readyMessages(group.messages);
      if (this.disposed || readyMessages.length === 0) continue;
      const active: ActiveGroup = { key, messages: group.messages, controller: new AbortController(), superseded: false };
      this.active = active;
      try {
        await this.invoke(readyMessages, {
          signal: active.controller.signal,
          isSuperseded: () => active.superseded || this.disposed,
          supersedeIfPending: () => {
            if (active.superseded) return true;
            if (!this.groups.get(active.key)?.messages.length) return false;
            this.supersedeActive(active.key);
            return true;
          },
        });
      } catch (reason) {
        if (!active.superseded && !this.disposed) throw reason;
      } finally {
        if (this.active === active) this.active = null;
      }
      if (active.superseded && !this.disposed) {
        this.requeueActive(active);
        // 재호출에도 debounce를 적용해 바로 뒤따르는 B/C를 최종 batch 하나로 모은다.
        return;
      }
    }
  }
}
