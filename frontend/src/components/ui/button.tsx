import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";

import { cn } from "./utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[transform,box-shadow,background-color,color,border-color] duration-fast ease-standard active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:shadow-focus-ring aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-elev-1 hover:shadow-elev-2",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-elev-1 hover:shadow-elev-2 focus-visible:ring-destructive/20 dark:focus-visible:ring-destructive/40 dark:bg-destructive/60",
        outline:
          "border border-border bg-background text-foreground hover:bg-surface-2 hover:border-primary/30 dark:bg-input/30 dark:border-input dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost:
          "hover:bg-surface-2 hover:text-foreground dark:hover:bg-accent/50",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        sm: "h-8 rounded-md gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 rounded-md px-6 has-[>svg]:px-4",
        icon: "size-9 rounded-md",
        "icon-sm": "size-8 rounded-md",
        pill: "h-9 rounded-pill px-5",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

type ButtonProps = React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    /** 加载中：禁用 + 左前置 spinner + 隐藏原图标。不改变按钮宽度（避免抖动）。 */
    loading?: boolean;
    /** 左图标（非 loading 时） */
    iconLeft?: React.ReactNode;
    /** 右图标 */
    iconRight?: React.ReactNode;
  };

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      disabled,
      iconLeft,
      iconRight,
      children,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : "button";
    const isDisabled = disabled || loading;

    // asChild 模式下无法注入 Loader2 / icon，保持 Slot 行为不变
    if (asChild) {
      return (
        <Comp
          data-slot="button"
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          aria-disabled={isDisabled || undefined}
          {...props}
        >
          {children}
        </Comp>
      );
    }

    return (
      <Comp
        data-slot="button"
        data-loading={loading || undefined}
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? <Loader2 className="animate-spin" /> : iconLeft}
        {children}
        {!loading && iconRight}
      </Comp>
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
export type { ButtonProps };
