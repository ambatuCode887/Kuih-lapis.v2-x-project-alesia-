import { Slot } from '@radix-ui/react-slot';
import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface Props extends HTMLAttributes<HTMLElement> {
  asChild?: boolean;
}

export function Card({ className, asChild, ...rest }: Props) {
  const Comp = asChild ? Slot : 'div';
  return (
    <Comp
      className={cn('rounded-card glass border-2 border-line-strong p-4 text-ink', className)}
      {...rest}
    />
  );
}
