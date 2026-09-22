/** 이미 저장된 AI 응답의 문장만 발췌한다. 별도 사실이나 판단을 만들지 않는다. */
export const bankAiSummary = (content: string): string => {
  const lines = content.replace(/\r\n?/gu, '\n').split('\n').map((line) => line.trim()).filter(Boolean);
  const line = lines.find((item) => !/^\[[^\]]+\]$/u.test(item) && !/^#{1,6}\s+[^.!?。]+$/u.test(item)) ?? lines[0] ?? '';
  const plain = line.replace(/^\s*(?:[-*]\s+|\d+\.\s+)/u, '').replace(/\*\*/gu, '').trim();
  return plain.split(/(?<=[.!?。])\s+/u)[0] ?? '';
};
