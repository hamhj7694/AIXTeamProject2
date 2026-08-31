import React from 'react';
import { cn } from '../../utils/helpers';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  loading?: boolean;
  children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      fullWidth = false,
      loading = false,
      disabled = false,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'font-semibold transition-all duration-200 rounded-xl border border-slate-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed';

    const variantStyles = {
      primary: 'bg-slate-900 text-white border-slate-900 hover:bg-slate-800 focus:ring-slate-500',
      secondary: 'bg-slate-100 text-slate-800 border-slate-200 hover:bg-slate-200 focus:ring-slate-400',
      danger: 'bg-rose-600 text-white border-rose-600 hover:bg-rose-700 focus:ring-rose-500',
      success: 'bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-700 focus:ring-emerald-500',
      ghost: 'bg-transparent text-slate-700 border-transparent hover:bg-slate-100 focus:ring-slate-400',
    };

    const sizeStyles = {
      sm: 'px-3.5 py-2 text-sm',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-5 py-3 text-sm',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          fullWidth && 'w-full',
          className
        )}
        {...props}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
