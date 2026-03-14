"use client";

import { ButtonHTMLAttributes, forwardRef, AnchorHTMLAttributes } from "react";
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

const variantStyles: Record<Variant, string> = {
  primary: "border-transparent bg-[rgba(var(--ink-950),0.94)] text-[rgb(var(--paper-soft))] shadow-[0_20px_48px_-28px_rgba(var(--shadow),0.72)] hover:-translate-y-0.5 hover:bg-[rgba(var(--ink-950),0.88)] focus-visible:ring-[rgba(var(--accent),0.24)]",
  secondary: "border-transparent bg-[rgba(var(--accent),0.9)] text-[rgb(var(--paper-soft))] shadow-[0_18px_42px_-28px_rgba(var(--shadow),0.58)] hover:-translate-y-0.5 hover:bg-[rgba(var(--accent),0.82)] focus-visible:ring-[rgba(var(--accent),0.22)]",
  outline: "border-[rgba(var(--line),0.2)] bg-[rgba(255,255,255,0.48)] text-[rgb(var(--ink-900))] hover:-translate-y-0.5 hover:bg-[rgba(255,255,255,0.72)] focus-visible:ring-[rgba(var(--accent),0.12)]",
  ghost: "border-transparent bg-transparent text-[rgb(var(--ink-800))] hover:bg-[rgba(var(--ink-950),0.04)] focus-visible:ring-[rgba(var(--accent),0.12)]",
  danger: "border-transparent bg-[rgba(var(--danger),0.94)] text-[rgb(var(--paper-soft))] shadow-[0_18px_40px_-26px_rgba(var(--danger),0.58)] hover:-translate-y-0.5 hover:bg-[rgba(var(--danger),0.86)] focus-visible:ring-[rgba(var(--danger),0.22)]",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-4 py-2 text-sm",
  md: "px-5 py-2.5 text-sm",
  lg: "px-7 py-3.5 text-base",
};

const baseStyles = "inline-flex items-center justify-center rounded-full border font-medium tracking-[0.08em] transition-all duration-200 focus:outline-none focus-visible:ring-4 disabled:cursor-not-allowed disabled:opacity-50 disabled:translate-y-0";

// Inner button/link renderer
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
    const widthClass = fullWidth ? "w-full" : "";
    const combinedClassName = `${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${widthClass} ${className}`.trim();

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
