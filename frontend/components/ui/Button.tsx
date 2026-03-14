"use client";

import { ButtonHTMLAttributes, forwardRef, AnchorHTMLAttributes, useMemo } from "react";
import Link from "next/link";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface BaseButtonProps {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
}

interface ButtonAsButton extends BaseButtonProps, Omit<ButtonHTMLAttributes<HTMLButtonElement>, "size"> {
  href?: never;
  disabled?: boolean;
}

interface ButtonAsLink extends BaseButtonProps, Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "size"> {
  href: string;
  prefetch?: boolean;
  replace?: boolean;
  scroll?: boolean;
  disabled?: never;
}

type ButtonProps = ButtonAsButton | ButtonAsLink;

// Performance: Extract static object outside to prevent recreation
const variantStyles: Record<Variant, string> = {
  primary: "border-transparent bg-ink-950/90 text-paper-soft shadow-lg hover:-translate-y-[2px] active:translate-y-0 active:scale-[0.98] hover:bg-ink-900 focus-visible:ring-seal/30",
  secondary: "border-transparent bg-seal/90 text-white shadow-md hover:-translate-y-[2px] active:translate-y-0 active:scale-[0.98] hover:bg-seal focus-visible:ring-seal/30",
  outline: "border-line/40 bg-white/40 text-ink-900 hover:-translate-y-[2px] active:translate-y-0 active:scale-[0.98] hover:bg-white/70 focus-visible:ring-seal/20 backdrop-blur-sm",
  ghost: "border-transparent bg-transparent text-ink-800 hover:bg-ink-950/5 active:scale-[0.98] focus-visible:ring-seal/20",
  danger: "border-transparent bg-red-800/90 text-white shadow-md hover:-translate-y-[2px] active:translate-y-0 active:scale-[0.98] hover:bg-red-800 focus-visible:ring-red-800/30",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-6 py-2.5 text-sm",
  lg: "px-8 py-3.5 text-base",
};

// Base styles incorporating hardware acceleration for smooth transform
const baseStyles = "inline-flex items-center justify-center rounded-lg border font-medium tracking-[0.05em] transition-all duration-300 ease-out will-change-transform focus:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-50 disabled:translate-y-0 disabled:active:scale-100 disabled:hover:-translate-y-0";

const ButtonInner = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      fullWidth = false,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    // Memoize className to skip expensive trims when props haven't changed
    const combinedClassName = useMemo(() => {
      const widthClass = fullWidth ? "w-full" : "";
      return `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${widthClass} ${className}`.trim();
    }, [variant, size, fullWidth, className]);

    if ("href" in props && props.href) {
      const { href, prefetch, replace, scroll, ...anchorProps } = props;
      return (
        <Link
          href={href}
          prefetch={prefetch}
          replace={replace}
          scroll={scroll}
          ref={ref as React.Ref<HTMLAnchorElement>}
          className={combinedClassName}
          {...anchorProps}
        >
          {children}
        </Link>
      );
    }

    const { disabled, ...buttonProps } = props as ButtonAsButton;
    return (
      <button
        ref={ref as React.Ref<HTMLButtonElement>}
        className={combinedClassName}
        disabled={disabled}
        {...buttonProps}
      >
        {children}
      </button>
    );
  }
);

ButtonInner.displayName = "ButtonInner";

export const Button = ButtonInner;
