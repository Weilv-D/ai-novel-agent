import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  testId?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id, testId, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const baseStyles = "w-full rounded-lg border border-line/60 bg-white/70 px-4 py-3 text-ink-950 shadow-inner backdrop-blur-sm transition-all duration-300 placeholder:text-ink-600/60 focus:outline-none focus:ring-2 focus:ring-seal/30 focus:border-seal/50 focus:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60";
    const errorStyles = error ? "border-red-700/50 focus:border-red-700/60 focus:ring-red-700/30 bg-red-50/60" : "";

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
          <p className="mt-2 text-xs text-red-800 tracking-wide">{error}</p>
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
    const baseStyles = "min-h-[120px] w-full rounded-lg border border-line/60 bg-white/70 px-4 py-3 text-ink-950 shadow-inner backdrop-blur-sm transition-all duration-300 placeholder:text-ink-600/60 focus:outline-none focus:ring-2 focus:ring-seal/30 focus:border-seal/50 focus:bg-white/90 disabled:cursor-not-allowed disabled:opacity-60";
    const errorStyles = error ? "border-red-700/50 focus:border-red-700/60 focus:ring-red-700/30 bg-red-50/60" : "";

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
          <p className="mt-2 text-xs text-red-800 tracking-wide">{error}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
