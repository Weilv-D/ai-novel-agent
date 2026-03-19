/**
 * Mobile Navigation Component
 *
 * Provides a responsive navigation experience for mobile devices.
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  {
    href: "/projects",
    label: "项目",
    icon: (
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v1M7 5a2 2 0 012-2h6a2 2 0 012 2v1" />
      </svg>
    ),
  },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname() ?? "";

  const toggleMenu = () => setIsOpen(!isOpen);
  const closeMenu = () => setIsOpen(false);

  return (
    <>
      {/* Mobile menu button - only visible on small screens */}
      <button
        onClick={toggleMenu}
        className="fixed bottom-6 left-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[rgb(var(--ink-950))] text-[rgb(var(--paper-soft))] shadow-lg md:hidden"
        aria-label="Toggle menu"
        aria-expanded={isOpen}
      >
        <svg
          className={`h-6 w-6 transition-transform duration-300 ${isOpen ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          {isOpen ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Mobile menu overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-[rgba(var(--ink-950),0.5)] backdrop-blur-sm md:hidden"
          onClick={closeMenu}
          aria-hidden="true"
        />
      )}

      {/* Mobile menu panel */}
      <div
        className={`fixed bottom-24 left-6 z-30 w-[calc(100vw-3rem)] max-w-[300px] rounded-[1.2rem] border border-[rgba(var(--line),0.2)] bg-[rgba(var(--paper),0.98)] p-4 shadow-xl backdrop-blur-md transition-all duration-300 md:hidden ${
          isOpen
            ? "translate-y-0 opacity-100"
            : "translate-y-4 opacity-0 pointer-events-none"
        }`}
      >
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMenu}
                className={`flex items-center gap-3 rounded-[0.75rem] px-4 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[rgba(var(--ink-950),0.08)] text-[rgb(var(--ink-950))]"
                    : "text-[rgb(var(--ink-800))] hover:bg-[rgba(var(--ink-950),0.04)]"
                }`}
              >
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}
