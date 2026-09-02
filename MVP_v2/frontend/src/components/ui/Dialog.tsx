import React, { useState } from 'react';
import { cn } from '../../utils/helpers';

interface DialogProps {
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

interface DialogContentProps {
  children: React.ReactNode;
  className?: string;
}

interface DialogTriggerProps {
  children: React.ReactNode;
  onClick?: () => void;
}

export const Dialog: React.FC<DialogProps> & {
  Trigger: React.FC<DialogTriggerProps>;
  Content: React.FC<DialogContentProps>;
  Close: React.FC<{ onClick?: () => void; children?: React.ReactNode }>;
} = ({ open, onOpenChange, children }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      {children}
    </div>
  );
};

Dialog.Trigger = ({ children, onClick }) => (
  <button onClick={onClick} className="cursor-pointer">
    {children}
  </button>
);

Dialog.Content = ({ children, className }) => (
  <div
    className={cn(
      'bg-white rounded-lg shadow-lg max-w-md w-full mx-4 max-h-[90vh] overflow-auto',
      className
    )}
  >
    {children}
  </div>
);

Dialog.Close = ({ onClick, children }) => (
  <button
    onClick={onClick}
    className="px-4 py-2 bg-gray-200 text-gray-900 rounded hover:bg-gray-300"
  >
    {children || '닫기'}
  </button>
);

Dialog.displayName = 'Dialog';
