import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  testId?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id, testId, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const baseStyles = "w-full rounded-lg border border-line/60 bg-[var(--field-surface)] px-4 py-3 text-ink-950 shadow-inner backdrop-blur-sm transition-all duration-300 placeholder:text-ink-700 focus:outline-none focus:ring-2 focus:ring-seal/30 focus:border-seal/50 focus:bg-[var(--field-surface-focus)] disabled:cursor-not-allowed disabled:opacity-60";
    const errorStyles = error ? "border-[rgba(var(--danger),0.45)] focus:border-[rgba(var(--danger),0.6)] focus:ring-[rgba(var(--danger),0.3)] bg-[rgba(var(--danger),0.08)]" : "";

    return (
      <div className="w-full" data-testid={testId ? `${testId}-wrapper` : undefined}>
        {label && (
          <label
            htmlFor={inputId}
            className="block mb-2 text-sm font-medium tracking-wider text-ink-800"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`${baseStyles} ${errorStyles} ${className}`}
          data-testid={testId}
          {...props}
        />
        {error && (
          <p className="mt-2 text-xs text-[rgb(var(--danger))] tracking-wide">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  testId?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = "", id, testId, ...props }, ref) => {
    const textareaId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const baseStyles = "min-h-[120px] w-full rounded-lg border border-line/60 bg-[var(--field-surface)] px-4 py-3 text-ink-950 shadow-inner backdrop-blur-sm transition-all duration-300 placeholder:text-ink-700 focus:outline-none focus:ring-2 focus:ring-seal/30 focus:border-seal/50 focus:bg-[var(--field-surface-focus)] disabled:cursor-not-allowed disabled:opacity-60";
    const errorStyles = error ? "border-[rgba(var(--danger),0.45)] focus:border-[rgba(var(--danger),0.6)] focus:ring-[rgba(var(--danger),0.3)] bg-[rgba(var(--danger),0.08)]" : "";

    return (
      <div className="w-full" data-testid={testId ? `${testId}-wrapper` : undefined}>
        {label && (
          <label
            htmlFor={textareaId}
            className="block mb-2 text-sm font-medium tracking-wider text-ink-800"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={`${baseStyles} ${errorStyles} ${className}`}
          data-testid={testId}
          {...props}
        />
        {error && (
          <p className="mt-2 text-xs text-[rgb(var(--danger))] tracking-wide">{error}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
