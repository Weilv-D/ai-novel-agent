"use client";

import { ButtonHTMLAttributes, forwardRef, AnchorHTMLAttributes, useMemo } from "react";
import Link from "next/link";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface BaseButtonProps {
  variant?: Variant;
  size?: Size;
  fullWidth?: boolean;
  testId?: string;
  loading?: boolean;
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

const variantStyles: Record<Variant, string> = {
  primary: "border-transparent bg-ink-950 text-paper-soft shadow-lg hover:-translate-y-[2px] hover:bg-ink-900 hover:shadow-xl active:translate-y-0 active:scale-[0.98] focus-visible:ring-seal/40",
  secondary: "border-transparent bg-seal text-white shadow-md hover:-translate-y-[2px] hover:bg-seal-dark hover:shadow-lg active:translate-y-0 active:scale-[0.98] focus-visible:ring-seal/40",
  outline: "border-line/50 bg-white/60 text-ink-900 hover:-translate-y-[2px] hover:bg-white/90 hover:border-line/70 active:translate-y-0 active:scale-[0.98] focus-visible:ring-seal/30 backdrop-blur-sm",
  ghost: "border-transparent bg-transparent text-ink-800 hover:bg-ink-950/8 active:scale-[0.98] focus-visible:ring-seal/30",
  danger: "border-transparent bg-red-800 text-white shadow-md hover:-translate-y-[2px] hover:bg-red-700 hover:shadow-lg active:translate-y-0 active:scale-[0.98] focus-visible:ring-red-800/40",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-6 py-2.5 text-sm",
  lg: "px-8 py-3.5 text-base",
};

const baseStyles = "inline-flex items-center justify-center gap-2 rounded-lg border font-medium tracking-[0.05em] transition-all duration-300 ease-out will-change-transform focus:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-50 disabled:translate-y-0 disabled:active:scale-100 disabled:hover:-translate-y-0";

function LoadingSpinner({ size }: { size: Size }) {
  const spinnerSize = size === "sm" ? "h-3 w-3" : size === "lg" ? "h-5 w-5" : "h-4 w-4";
  return (
    <svg
      className={`animate-button-spin ${spinnerSize}`}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

const ButtonInner = forwardRef<HTMLButtonElement | HTMLAnchorElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      fullWidth = false,
      loading = false,
      className = "",
      testId,
      children,
      ...props
    },
    ref
  ) => {
    const combinedClassName = useMemo(() => {
      const widthClass = fullWidth ? "w-full" : "";
      return `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${widthClass} ${className}`.trim();
    }, [variant, size, fullWidth, className]);

    const isLoading = loading && !("href" in props);

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
          data-testid={testId}
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
        disabled={disabled || isLoading}
        data-testid={testId}
        aria-busy={isLoading}
        {...buttonProps}
      >
        {isLoading && <LoadingSpinner size={size} />}
        {children}
      </button>
    );
  }
);

ButtonInner.displayName = "ButtonInner";

export const Button = ButtonInner;
