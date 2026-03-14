import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const baseStyles = "w-full rounded-[1rem] border border-[rgba(var(--line),0.18)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(247,244,238,0.95))] px-4 py-3 text-[rgb(var(--ink-950))] shadow-[0_18px_42px_-34px_rgba(var(--shadow),0.55)] transition-all duration-200 placeholder:text-[rgb(var(--ink-600))] focus:outline-none focus:ring-4 focus:ring-[rgba(var(--accent),0.08)] focus:border-[rgba(var(--accent),0.28)] disabled:cursor-not-allowed disabled:opacity-60";
    const errorStyles = error ? "border-[rgba(var(--danger),0.35)] focus:border-[rgba(var(--danger),0.4)] focus:ring-[rgba(var(--danger),0.08)]" : "";

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="ink-label"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`${baseStyles} ${errorStyles} ${className}`}
          {...props}
        />
        {error && (
          <p className="mt-2 text-sm text-[rgb(var(--danger))]">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
    const textareaId = id || label?.toLowerCase().replace(/\s+/g, "-");
    const baseStyles = "min-h-[120px] w-full rounded-[1rem] border border-[rgba(var(--line),0.18)] bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(247,244,238,0.95))] px-4 py-3 text-[rgb(var(--ink-950))] shadow-[0_18px_42px_-34px_rgba(var(--shadow),0.55)] transition-all duration-200 placeholder:text-[rgb(var(--ink-600))] focus:outline-none focus:ring-4 focus:ring-[rgba(var(--accent),0.08)] focus:border-[rgba(var(--accent),0.28)] disabled:cursor-not-allowed disabled:opacity-60";
    const errorStyles = error ? "border-[rgba(var(--danger),0.35)] focus:border-[rgba(var(--danger),0.4)] focus:ring-[rgba(var(--danger),0.08)]" : "";

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textareaId}
            className="ink-label"
          >
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          className={`${baseStyles} ${errorStyles} ${className}`}
          {...props}
        />
        {error && (
          <p className="mt-2 text-sm text-[rgb(var(--danger))]">{error}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
