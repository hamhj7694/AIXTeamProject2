import React, { useState } from 'react';
import { AlertTriangle, Loader2, X } from 'lucide-react';

interface Props {
  title: string;
  description: string;
  confirmLabel: string;
  danger?: boolean;
  noteLabel?: string;
  notePlaceholder?: string;
  onConfirm: (password: string, note: string) => Promise<void>;
  onClose: () => void;
}

export const AdminCaseDialog: React.FC<Props> = ({
  title, description, confirmLabel, danger = false, noteLabel, notePlaceholder, onConfirm, onClose,
}) => {
  const [password, setPassword] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!password || busy) return;
    setBusy(true); setError('');
    try {
      await onConfirm(password, note.trim());
      onClose();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '요청을 처리하지 못했습니다.');
    } finally {
      setBusy(false);
    }
  };

  return <div className="dialog-backdrop" role="presentation">
    <form className="dialog admin-case-dialog" onSubmit={(event) => void submit(event)} role="dialog" aria-modal="true" aria-labelledby="admin-case-dialog-title">
      <header><div><h2 id="admin-case-dialog-title">{title}</h2><p>{description}</p></div><button type="button" className="icon-button" onClick={onClose} disabled={busy} aria-label="닫기"><X size={18}/></button></header>
      <div className="dialog-body form-grid">
        {danger && <p className="admin-danger-notice"><AlertTriangle size={16}/><span>영구 삭제 후에는 사건과 연결된 기록을 복구할 수 없습니다.</span></p>}
        {noteLabel && <label>{noteLabel}<textarea rows={3} maxLength={10000} value={note} onChange={(event) => setNote(event.target.value)} placeholder={notePlaceholder}/></label>}
        <label>관리자 암호<input autoFocus type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="관리자 암호 입력"/></label>
        {error && <div className="dialog-error"><AlertTriangle size={15}/><span>{error}</span></div>}
      </div>
      <footer className="dialog-footer"><button type="button" className="secondary-action" onClick={onClose} disabled={busy}>취소</button><button type="submit" className={danger ? 'danger-action' : 'primary-action'} disabled={!password || busy}>{busy && <Loader2 className="spin" size={14}/>} {confirmLabel}</button></footer>
    </form>
  </div>;
};
