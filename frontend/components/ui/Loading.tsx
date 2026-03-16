interface LoadingProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeStyles: Record<NonNullable<LoadingProps["size"]>, string> = {
  sm: "h-4 w-4 border-2",
  md: "h-8 w-8 border-[3px]",
  lg: "h-12 w-12 border-4",
};

export function Loading({ size = "md", className = "" }: LoadingProps) {
  return (
    <div className="flex items-center justify-center" role="status" aria-label="Loading">
      <svg
        className={`animate-spin rounded-full border-line/30 border-t-seal text-seal ${sizeStyles[size]} ${className}`}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
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
      <span className="sr-only">研墨中...</span>
    </div>
  );
}

interface LoadingSpinnerProps extends LoadingProps {
  text?: string;
}

export function LoadingSpinner({ size = "md", text, className = "" }: LoadingSpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 ${className}`}>
      <Loading size={size} />
      {text && <p className="text-sm tracking-widest text-ink-800 animate-pulse font-serif">{text}</p>}
    </div>
  );
}
