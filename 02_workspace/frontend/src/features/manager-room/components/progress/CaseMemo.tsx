import React, { FormEvent, useState } from 'react';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { Card } from '../../../../components/ui/Card';
import { ManagerRoomMemoItem } from '../../types';

interface CaseMemoProps {
  memos: ManagerRoomMemoItem[];
  onMemosChange: React.Dispatch<React.SetStateAction<ManagerRoomMemoItem[]>>;
  embedded?: boolean;
  scrollableList?: boolean;
}

export const CaseMemo: React.FC<CaseMemoProps> = ({
  memos,
  onMemosChange,
  embedded = false,
  scrollableList = false,
}) => {
  const [newMemo, setNewMemo] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedMemo = newMemo.trim();
    if (!trimmedMemo) return;
    const memoId = `manager-memo-${Date.now()}`;

    onMemosChange((currentMemos) => [
      ...currentMemos,
      {
        id: memoId,
        content: trimmedMemo,
      },
    ]);
    setNewMemo('');
  };

  const startEditing = (memo: ManagerRoomMemoItem) => {
    setEditingId(memo.id);
    setEditingValue(memo.content);
  };

  const cancelEditing = () => {
    setEditingId(null);
    setEditingValue('');
  };

  const saveEditing = (id: string) => {
    const trimmedValue = editingValue.trim();
    if (!trimmedValue) return;

    // 선택한 항목만 교체해 다른 메모의 내용과 순서를 보존한다.
    onMemosChange((currentMemos) =>
      currentMemos.map((memo) =>
        memo.id === id ? { ...memo, content: trimmedValue } : memo
      )
    );
    cancelEditing();
  };

  const deleteMemo = (id: string) => {
    onMemosChange((currentMemos) =>
      currentMemos.filter((memo) => memo.id !== id)
    );

    if (editingId === id) {
      cancelEditing();
    }
  };

  const content = (
    <section aria-labelledby="case-memo-title">
        <div className="flex flex-wrap items-center gap-2">
          <h2 id="case-memo-title" className="text-base font-extrabold text-slate-950">
            내부 메모
          </h2>
          <Badge variant="default">Local</Badge>
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          현재 Case 조사 중 필요한 내용을 간단히 기록합니다.
        </p>

        <form onSubmit={handleSubmit} className="mt-3">
          <label htmlFor="manager-case-memo" className="sr-only">
            담당자 내부 메모
          </label>
          <textarea
            id="manager-case-memo"
            value={newMemo}
            onChange={(event) => setNewMemo(event.target.value)}
            rows={3}
            placeholder="예: 고객이 수취인을 기존 지인이라고 설명했는지 추가 확인 필요"
            className="w-full resize-none rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm leading-5 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="text-[11px] text-slate-400">
              새로고침하면 초기화됩니다.
            </span>
            <Button type="submit" size="sm" disabled={!newMemo.trim()}>
              메모 추가
            </Button>
          </div>
        </form>

        <div
          className={`mt-3 border-t border-slate-200 pt-3 ${
            scrollableList
              ? 'max-h-64 overflow-y-auto overscroll-contain pr-1 [scrollbar-width:thin]'
              : ''
          }`}
        >
          {memos.length === 0 ? (
            <p className="text-xs text-slate-400">아직 작성된 메모가 없습니다.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {memos.map((memo) => {
                const isEditing = editingId === memo.id;

                return (
                  <li key={memo.id} className="py-3 first:pt-0 last:pb-0">
                    {isEditing ? (
                      <div>
                        <label htmlFor={`edit-${memo.id}`} className="sr-only">
                          내부 메모 수정
                        </label>
                        <textarea
                          id={`edit-${memo.id}`}
                          value={editingValue}
                          onChange={(event) => setEditingValue(event.target.value)}
                          rows={3}
                          className="w-full resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm leading-5 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
                        />
                        <div className="mt-2 flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={cancelEditing}
                            className="px-2 py-1 text-xs font-bold text-slate-500 hover:text-slate-800"
                          >
                            취소
                          </button>
                          <button
                            type="button"
                            onClick={() => saveEditing(memo.id)}
                            disabled={!editingValue.trim()}
                            className="rounded-md bg-blue-600 px-2.5 py-1 text-xs font-bold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
                          >
                            저장
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-start justify-between gap-3">
                        <p className="min-w-0 whitespace-pre-wrap text-sm leading-5 text-slate-700">
                          {memo.content}
                        </p>
                        <div className="flex shrink-0 items-center gap-1">
                          <button
                            type="button"
                            onClick={() => startEditing(memo)}
                            className="px-2 py-1 text-xs font-bold text-slate-500 hover:text-blue-700"
                          >
                            수정
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteMemo(memo.id)}
                            className="px-2 py-1 text-xs font-bold text-rose-500 hover:text-rose-700"
                          >
                            삭제
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
    </section>
  );

  return embedded ? (
    content
  ) : (
    <Card className="rounded-xl border-slate-200 p-4 shadow-sm">
      {content}
    </Card>
  );
};
