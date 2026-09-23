import { Building2, ChevronUp, CreditCard, ListChecks } from 'lucide-react';
import type { MouseEvent } from 'react';

export type BankCardKind = 'transaction' | 'fds' | 'additionalLookup';

const options: Array<{ value: BankCardKind; icon: string; label: string }> = [
  { value: 'fds', icon: '📊', label: 'FDS 분석 결과' },
  { value: 'additionalLookup', icon: '💸', label: '송금 기록 조회' },
];

type BankCardMenuProps = {
  value: BankCardKind | null;
  onChange: (value: BankCardKind) => void;
  onOpenVerification: () => void;
  onOpenAction: () => void;
};

export function BankCardMenu({ value: _value, onChange, onOpenVerification, onOpenAction }: BankCardMenuProps) {
  const closePopover = (event: MouseEvent<HTMLButtonElement>) => {
    event.currentTarget.closest('details')?.removeAttribute('open');
  };

  return <details className="bank-card-menu">
    <summary><CreditCard size={14}/><span>사건 자료</span><ChevronUp size={14}/></summary>
    <div className="bank-card-menu-popover" role="menu">
      {options.map((option) => <button key={option.value} type="button" role="menuitem" onClick={(event) => { onChange(option.value); closePopover(event); }}><span aria-hidden="true">{option.icon}</span>{option.label}</button>)}
      <button type="button" role="menuitem" onClick={(event) => { onOpenVerification(); closePopover(event); }}><Building2 size={13}/>기관 확인</button>
      <button type="button" role="menuitem" onClick={(event) => { onOpenAction(); closePopover(event); }}><ListChecks size={13}/>체크리스트</button>
    </div>
  </details>;
}
