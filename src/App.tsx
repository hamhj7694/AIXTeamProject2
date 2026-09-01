import React, { useEffect, useState } from 'react';
import { AppRoutes } from './router/routes';
import { VoiceCallPopup } from './components/voice/VoiceCallPopup';
import { closeVoiceCall, readVoiceCallState } from './components/voice/voiceCallState';
import './index.css';

function App() {
  const [voiceCall, setVoiceCall] = useState(readVoiceCallState);
  useEffect(() => { const sync = () => setVoiceCall(readVoiceCallState()); window.addEventListener('voice-call-change', sync); return () => window.removeEventListener('voice-call-change', sync); }, []);
  return <><AppRoutes /><VoiceCallPopup open={voiceCall.open} role={voiceCall.role} onClose={closeVoiceCall} onCallStarted={() => window.dispatchEvent(new Event('voice-call-started'))} onRecordingReady={(url) => window.dispatchEvent(new CustomEvent('voice-call-recording-ready', { detail: { url } }))} /></>;
}

export default App;
