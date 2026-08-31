import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Header } from './Header';

interface AppLayoutProps {
  children: React.ReactNode;
}

const navItems = [
  { label: '상담', path: '/', icon: '◎' },
  { label: '안전안내', path: '/safety', icon: '✓' },
  { label: '기록', path: '/history', icon: '▣' },
  { label: '대응법', path: '/response-guide', icon: '☰' },
];

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation();

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 text-slate-800">
      <Header />
      <main className="flex-1 w-full pb-24">
        {children}
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-slate-200 bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-2 px-3 py-2">
          {navItems.map((item) => {
            const active = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={[
                  'flex flex-1 flex-col items-center justify-center rounded-xl px-2 py-2 text-[11px] font-medium transition-colors',
                  active
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100',
                ].join(' ')}
              >
                <span className="mb-1 text-base leading-none">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
};
