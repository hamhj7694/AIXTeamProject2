import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { CustomerSafetyRoom } from '../features/mvp-chat/CustomerSafetyRoom';
import { mvpChatApi, type CaseBundleV2, type MvpMessage } from '../services/mvpChatApi';

export const CustomerChatPage: React.FC = () => {
  const { caseId = '' } = useParams();
  const [bundle, setBundle] = useState<CaseBundleV2 | null>(null);
  const [messages, setMessages] = useState<MvpMessage[]>([]);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    const [nextBundle, nextMessages] = await Promise.all([mvpChatApi.getBundle(caseId, 'customer'), mvpChatApi.listMessages(caseId, 'CUSTOMER')]);
    setBundle(nextBundle); setMessages(nextMessages);
  }, [caseId]);
  useEffect(() => { load().catch((reason) => setError(reason instanceof Error ? reason.message : 'Case를 불러오지 못했습니다.')); }, [load]);
  useEffect(() => { const timer = window.setInterval(() => { load().catch(() => undefined); }, 3000); return () => window.clearInterval(timer); }, [load]);
  const send = async (content: string) => { setSending(true); try { const message = await mvpChatApi.createMessage(caseId, { actor_type: 'CUSTOMER', content, channel: 'CUSTOMER', audience: 'CUSTOMER' }); setMessages((items) => [...items, message]); } finally { setSending(false); } };
  return <AppLayout>
    {error && <p className="mx-auto mt-6 max-w-[1640px] rounded-xl bg-rose-50 p-3 text-sm font-semibold text-rose-700 lg:ml-[calc(16rem+1.5rem)]">{error}</p>}
    <CustomerSafetyRoom caseId={caseId} bundle={bundle} messages={messages} sending={sending} onSend={send} />
  </AppLayout>;
};
