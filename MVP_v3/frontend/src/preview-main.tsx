import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import CardPreview from './components/cards/CardPreview';
import './styles.css';

createRoot(document.getElementById('card-preview-root')!).render(<StrictMode><CardPreview /></StrictMode>);
