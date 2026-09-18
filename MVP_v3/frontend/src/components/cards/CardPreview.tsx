import BankTransactionCard from './BankTransactionCard';
import FdsResultCard from './FdsResultCard';
import AdditionalLookupCard from './AdditionalLookupCard';
import { mockAdditionalLookup, mockBankTransaction, mockFdsResult } from '../../mocks/cardMocks';

export default function CardPreview() { return <main style={{ display: 'grid', gap: 16, maxWidth: 760, padding: 24, margin: '0 auto', overflowY: 'auto' }}><BankTransactionCard {...mockBankTransaction} showSourceBadges /><FdsResultCard {...mockFdsResult} /><AdditionalLookupCard {...mockAdditionalLookup} onViewAll={() => undefined} /></main>; }
