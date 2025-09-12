import React from 'react';
import { cn } from '../../lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, ...props }, ref) => (
  <input
    className={cn('flex h-9 w-full rounded-md bg-gray-800 px-3 py-1 text-sm text-white placeholder-gray-400', className)}
    ref={ref}
    {...props}
  />
));
Input.displayName = 'Input';
