import type { ButtonHTMLAttributes, ReactNode } from "react";

/** Botão de ação sólido com a cor de destaque. Aceita as props usuais de button. */
export function AccentButton({
  children,
  className = "",
  style,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { children: ReactNode }) {
  return (
    <button
      {...props}
      className={`px-4 py-2 rounded-lg text-white text-sm disabled:opacity-50 ${className}`}
      style={{ backgroundColor: "var(--accent-color)", ...style }}
    >
      {children}
    </button>
  );
}
