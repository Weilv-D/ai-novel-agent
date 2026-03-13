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
  primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
  secondary: "bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500",
  outline: "border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-gray-300",
  ghost: "text-gray-700 hover:bg-gray-100 focus:ring-gray-200",
  danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

const baseStyles = "inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed";

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
