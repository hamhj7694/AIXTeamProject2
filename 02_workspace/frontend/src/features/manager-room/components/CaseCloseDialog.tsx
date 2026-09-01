import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { Dialog } from '../../../components/ui/Dialog';

interface CaseCloseDialogProps {
  open: boolean;
  mode: 'close' | 'refresh';
  onCancel: () => void;
  onConfirm: () => void;
}

export const CaseCloseDialog: React.FC<CaseCloseDialogProps> = ({
  open,
  mode,
  onCancel,
  onConfirm,
}) => {
  const isRefresh = mode === 'refresh';

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onCancel()}>
      <Dialog.Content className="overflow-hidden rounded-2xl border border-slate-200">
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="case-close-title"
          aria-describedby="case-close-description"
        >
          <div className="flex gap-3 border-b border-slate-100 p-5">
            <span
              className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${
                isRefresh
                  ? 'bg-blue-100 text-blue-600'
                  : 'bg-rose-100 text-rose-600'
              }`}
            >
              {isRefresh ? <RefreshCw size={20} /> : <AlertTriangle size={20} />}
            </span>
            <div>
              <h2 id="case-close-title" className="text-lg font-black text-slate-950">
                {isRefresh
                  ? '최종 리포트를 갱신하시겠습니까?'
                  : '이 사건을 종료하시겠습니까?'}
              </h2>
              <p id="case-close-description" className="mt-2 text-sm leading-6 text-slate-600">
                {isRefresh
                  ? '현재 수정된 사건 내용을 기준으로 최종 리포트를 갱신합니다.'
                  : '종료하면 현재까지의 조사 결과를 기준으로 최종 리포트가 생성됩니다.'}
              </p>
            </div>
          </div>

          <div className="flex justify-end gap-2 bg-slate-50 px-5 py-4">
            <Button type="button" variant="secondary" onClick={onCancel}>
              취소
            </Button>
            <Button
              type="button"
              variant={isRefresh ? 'primary' : 'danger'}
              onClick={onConfirm}
            >
              {isRefresh ? '리포트 갱신' : '사건 종료'}
            </Button>
          </div>
        </div>
      </Dialog.Content>
    </Dialog>
  );
};
