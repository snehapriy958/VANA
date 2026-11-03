import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-vana-forest focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-vana-forest text-vana-white shadow-subtle hover:bg-vana-forest/90 active:bg-vana-forest/95",
        secondary:
          "bg-vana-sage/20 text-vana-forest hover:bg-vana-sage/30 active:bg-vana-sage/40",
        outline:
          "border border-vana-charcoal/15 bg-transparent hover:bg-vana-charcoal/5 active:bg-vana-charcoal/10 text-vana-charcoal",
        ghost:
          "hover:bg-vana-charcoal/5 active:bg-vana-charcoal/10 text-vana-charcoal",
        destructive:
          "bg-vana-crimson text-white shadow-subtle hover:bg-vana-crimson/90 active:bg-vana-crimson/95",
        gold:
          "bg-vana-gold text-vana-charcoal font-semibold shadow-subtle hover:bg-vana-gold/90 active:bg-vana-gold/95",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-md px-3 text-xs",
        lg: "h-12 rounded-md px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
