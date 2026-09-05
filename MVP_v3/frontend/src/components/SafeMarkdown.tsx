import React from 'react';

interface Props {
  content: string;
  className?: string;
}

const inlinePattern = /\*\*([^*]+)\*\*|__([^_]+)__|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|\*([^*]+)\*|_([^_]+)_/gu;
const orderedPattern = /^\s*\d+[.)]\s+(.+)$/u;
const unorderedPattern = /^\s*[-*+]\s+(.+)$/u;
const headingPattern = /^(#{1,3})\s+(.+)$/u;

const renderInline = (text: string, keyPrefix: string): React.ReactNode[] => {
  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;
  let index = 0;

  while ((match = inlinePattern.exec(text)) !== null) {
    if (match.index > cursor) nodes.push(text.slice(cursor, match.index));
    const key = `${keyPrefix}-${index++}`;
    if (match[1] || match[2]) nodes.push(<strong key={key}>{match[1] || match[2]}</strong>);
    else if (match[3]) nodes.push(<code key={key}>{match[3]}</code>);
    else if (match[4] && match[5]) nodes.push(<a key={key} href={match[5]} target="_blank" rel="noreferrer">{match[4]}</a>);
    else nodes.push(<em key={key}>{match[6] || match[7]}</em>);
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
};

export const SafeMarkdown: React.FC<Props> = ({ content, className = '' }) => {
  const lines = String(content || '').replace(/\r\n?/gu, '\n').split('\n');
  const blocks: React.ReactNode[] = [];
  let lineIndex = 0;

  while (lineIndex < lines.length) {
    const line = lines[lineIndex];
    if (!line.trim()) { lineIndex += 1; continue; }

    const heading = line.match(headingPattern);
    if (heading) {
      const level = heading[1].length;
      const Tag = (`h${level}` as keyof JSX.IntrinsicElements);
      blocks.push(<Tag key={`heading-${lineIndex}`}>{renderInline(heading[2], `heading-${lineIndex}`)}</Tag>);
      lineIndex += 1;
      continue;
    }

    const firstOrdered = line.match(orderedPattern);
    if (firstOrdered) {
      const items: string[] = [];
      while (lineIndex < lines.length) {
        const item = lines[lineIndex].match(orderedPattern);
        if (item) {
          items.push(item[1]); lineIndex += 1;
          continue;
        }
        // LLM은 번호 항목 사이에 빈 줄을 자주 넣는다. 다음 내용도 번호
        // 항목이면 같은 <ol>로 유지해 번호가 1부터 다시 시작되지 않게 한다.
        if (!lines[lineIndex].trim()) {
          let nextIndex = lineIndex + 1;
          while (nextIndex < lines.length && !lines[nextIndex].trim()) nextIndex += 1;
          if (nextIndex < lines.length && orderedPattern.test(lines[nextIndex])) {
            lineIndex = nextIndex;
            continue;
          }
        }
        break;
      }
      blocks.push(<ol key={`ordered-${lineIndex}`}>{items.map((item, index) => <li key={`ordered-item-${index}`}>{renderInline(item, `ordered-${index}`)}</li>)}</ol>);
      continue;
    }

    const firstUnordered = line.match(unorderedPattern);
    if (firstUnordered) {
      const items: string[] = [];
      while (lineIndex < lines.length) {
        const item = lines[lineIndex].match(unorderedPattern);
        if (!item) break;
        items.push(item[1]); lineIndex += 1;
      }
      blocks.push(<ul key={`unordered-${lineIndex}`}>{items.map((item, index) => <li key={`unordered-item-${index}`}>{renderInline(item, `unordered-${index}`)}</li>)}</ul>);
      continue;
    }

    const paragraph: string[] = [line];
    lineIndex += 1;
    while (lineIndex < lines.length && lines[lineIndex].trim() && !headingPattern.test(lines[lineIndex]) && !orderedPattern.test(lines[lineIndex]) && !unorderedPattern.test(lines[lineIndex])) {
      paragraph.push(lines[lineIndex]); lineIndex += 1;
    }
    blocks.push(<p key={`paragraph-${lineIndex}`}>{paragraph.map((part, index) => <React.Fragment key={`paragraph-line-${index}`}>{index > 0 && <br/>}{renderInline(part, `paragraph-${lineIndex}-${index}`)}</React.Fragment>)}</p>);
  }

  return <div className={`safe-markdown ${className}`.trim()}>{blocks}</div>;
};
