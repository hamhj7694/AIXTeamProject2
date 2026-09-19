import { ChevronUp, CreditCard } from 'lucide-react';

export type BankCardKind = 'transaction' | 'fds' | 'additionalLookup';

const options: Array<{ value: BankCardKind; label: string }> = [
  { value: 'transaction', label: '은행 거래 확인' },
  { value: 'fds', label: 'FDS 분석 결과' },
  { value: 'additionalLookup', label: '추가 조회 결과' },
];

export function BankCardMenu({ value: _value, onChange }: { value: BankCardKind | null; onChange: (value: BankCardKind) => void }) {
  return <details className="bank-card-menu">
    <summary><CreditCard size={14}/><span>사건 자료</span><ChevronUp size={14}/></summary>
    <div className="bank-card-menu-popover" role="menu">
      {options.map((option) => <button key={option.value} type="button" role="menuitem" onClick={(event) => { onChange(option.value); event.currentTarget.closest('details')?.removeAttribute('open'); }}>{option.label}</button>)}
    </div>
  </details>;
}
