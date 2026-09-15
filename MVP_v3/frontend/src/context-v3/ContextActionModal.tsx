import React, { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

type ContextActionModalProps = {
  title: string;
  description?: string;
  children: React.ReactNode;
  primaryLabel: string;
  onPrimary: () => void;
  onClose: () => void;
  busy?: boolean;
  primaryDisabled?: boolean;
};

export const ContextInlineError: React.FC<{ children?: React.ReactNode }> = ({ children }) => children ? <p className="context-inline-form-error context-dialog-error" role="alert">{children}</p> : null;

export const ContextTextArea: React.FC<React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }> = ({ label, id, ...props }) => {
  const generatedId = useId();
  const inputId = id ?? `context-textarea-${generatedId}`;
  return <label className="context-dialog-field" htmlFor={inputId}><span>{label}</span><textarea id={inputId} {...props}/></label>;
};

export const ContextActionModal: React.FC<ContextActionModalProps> = ({ title, description, children, primaryLabel, onPrimary, onClose, busy = false, primaryDisabled = false }) => {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape' && !busy) onClose(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [busy, onClose]);
  return <div className="context-dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <section className="context-action-modal" role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <header><div><h3 id={titleId}>{title}</h3>{description && <p>{description}</p>}</div><button ref={closeRef} type="button" className="context-dialog-close" onClick={onClose} disabled={busy} aria-label="닫기"><X size={16}/></button></header>
      <div className="context-dialog-body">{children}</div>
      <footer><button type="button" className="context-dialog-cancel" onClick={onClose} disabled={busy}>취소</button><button type="button" className="context-primary-action" onClick={onPrimary} disabled={busy || primaryDisabled}>{primaryLabel}</button></footer>
    </section>
  </div>;
};

export const ContextConfirmModal: React.FC<Omit<ContextActionModalProps, 'children'> & { children?: React.ReactNode }> = ({ children, ...props }) => <ContextActionModal {...props}>{children ?? <p className="context-dialog-confirm-copy">이 작업을 진행할까요?</p>}</ContextActionModal>;
