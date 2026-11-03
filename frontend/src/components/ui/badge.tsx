import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-vana-forest focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "bg-vana-charcoal text-white hover:bg-vana-charcoal/80",
        verified:
          "border border-vana-forest/25 bg-vana-forest/10 text-vana-forest font-semibold",
        pending:
          "border border-vana-gold/40 bg-vana-gold/15 text-[#8C6228] font-semibold",
        rejected:
          "border border-vana-crimson/25 bg-vana-crimson/10 text-vana-crimson font-semibold",
        sage:
          "border border-vana-sage/40 bg-vana-sage/20 text-vana-forest font-semibold",
        active:
          "border border-emerald-600/30 bg-emerald-50 text-emerald-800 font-semibold",
        neutral:
          "border border-vana-charcoal/20 bg-vana-ivory/60 text-vana-charcoal/80 font-medium",
        outline:
          "border border-vana-charcoal/20 text-vana-charcoal",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
