import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { heading, cardStyle } from '@/lib/design-tokens';

interface A2UICardShellProps {
  title?: string;
  subtitle?: string;
  headerAside?: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function A2UICardShell({
  title,
  subtitle,
  headerAside,
  children,
  actions,
  className,
  bodyClassName,
}: A2UICardShellProps) {
  return (
    <section
      data-a2ui-card
      className={cn(
        `${cardStyle.compact} overflow-hidden !p-0`,
        className,
      )}
    >
      {(title || subtitle || headerAside) && (
        <header
          data-a2ui-header
          className="flex items-start justify-between gap-3 border-b border-border/60 px-4 py-3"
        >
          <div className="min-w-0 space-y-1">
            {title ? <h3 className={`${heading.card} line-clamp-1`}>{title}</h3> : null}
            {subtitle ? <p className={`${heading.micro} line-clamp-2`}>{subtitle}</p> : null}
          </div>
          {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
        </header>
      )}
      <div data-a2ui-body className={cn('px-4 py-4', bodyClassName)}>
        {children}
      </div>
      {actions ? (
        <footer
          data-a2ui-actions
          className="flex flex-wrap items-center justify-end gap-2 border-t border-border/60 px-4 py-3"
        >
          {actions}
        </footer>
      ) : null}
    </section>
  );
}
