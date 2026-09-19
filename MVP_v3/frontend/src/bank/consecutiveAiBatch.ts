export const BANK_AI_BATCH_DELAY_MS = 1200;

export type ConsecutiveAiMessage = {
  caseId: string;
  requesterUserId: string;
  messageId: string;
  content: string;
  saved?: Promise<boolean>;
};

type PendingGroup = {
  messages: ConsecutiveAiMessage[];
  messageIds: Set<string>;
};

type TimerHandle = ReturnType<typeof setTimeout>;

const groupKey = (message: ConsecutiveAiMessage) => `${message.caseId}\u0000${message.requesterUserId}`;

export const buildConsecutiveAiPrompt = (messages: ConsecutiveAiMessage[]) => {
  const request = messages.map((message, index) => `${index + 1}. ${message.content}`).join('\n');
  return `[현재 요청 - 연속 메시지]\n\n${request}\n\n현재 Shared Case 맥락만 바탕으로, 동료에게 답하듯 자연스럽게 업무를 지원해 주세요. 확인되지 않은 사실은 추정하지 말고, 고객에게 자동 전송하거나 지급정지·신고 등 외부 조치를 완료한 것처럼 표현하지 마세요.`;
};

/**
 * 개별 MESSAGE 저장은 유지하면서 짧게 이어진 입력만 AI 요청 단위로 묶는다.
 * 실행 중 입력은 pending에 남겨 현재 응답 뒤에 직렬로 처리한다.
 */
export class ConsecutiveAiBatcher {
  private readonly groups = new Map<string, PendingGroup>();
  private timer: TimerHandle | null = null;
  private draining: Promise<void> | null = null;
  private disposed = false;

  constructor(
    private readonly invoke: (messages: ConsecutiveAiMessage[]) => Promise<void>,
    private readonly delayMs = BANK_AI_BATCH_DELAY_MS,
  ) {}

  enqueue(message: ConsecutiveAiMessage) {
    if (this.disposed) return;
    const key = groupKey(message);
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

  waitForIdle(): Promise<void> {
    return this.draining ?? Promise.resolve();
  }

  dispose() {
    this.disposed = true;
    this.clearTimer();
    this.groups.clear();
  }

  private schedule() {
    this.clearTimer();
    this.timer = setTimeout(() => { void this.flushNow(); }, this.delayMs);
  }

  private clearTimer() {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
  }

  private async drain() {
    while (!this.disposed && this.groups.size > 0) {
      const first = this.groups.entries().next().value as [string, PendingGroup] | undefined;
      if (!first) return;
      const [key, group] = first;
      this.groups.delete(key);

      // AI 호출 전에 각 원본 MESSAGE가 실제 저장됐는지 확인한다.
      const saved = await Promise.all(group.messages.map(async (message) => (
        message.saved ? await message.saved : true
      )));
      if (this.disposed) return;
      const readyMessages = group.messages.filter((_, index) => saved[index]);
      if (readyMessages.length > 0) await this.invoke(readyMessages);
    }
  }
}
