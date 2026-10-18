import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import type { ButtonHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

// Every size is at least 44px tall. Jade is only for the safe, primary action.
const button = cva(
  'inline-flex items-center justify-center gap-2 rounded-xl font-bold cursor-pointer disabled:cursor-not-allowed focus-visible:outline-3 focus-visible:outline-offset-3 focus-visible:outline-jade',
  {
    variants: {
      variant: {
        primary: 'bg-jade text-on-jade',
        outline: 'border-2 border-line-strong bg-card text-ink',
        quiet: 'text-ink-2 underline underline-offset-4',
      },
      size: {
        md: 'min-h-12 px-5 text-[1.0625rem]',
        lg: 'min-h-14 px-6 text-[1.2rem]',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
);

interface Props
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof button> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild, ...rest }: Props) {
  const Comp = asChild ? Slot : 'button';
  return <Comp className={cn(button({ variant, size }), className)} {...rest} />;
}
