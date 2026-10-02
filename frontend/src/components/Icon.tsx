const paths = {
  film: 'M4 4h16v16H4z M4 8h16M4 16h16M8 4v16M16 4v16',
  plus: 'M12 5v14M5 12h14',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  history: 'M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2',
  pause: 'M8 5v14M16 5v14',
  play: 'M8 5l11 7-11 7z',
  copy: 'M9 9h11v11H9zM15 9V4H4v11h5',
  download: 'M12 3v12M7 10l5 5 5-5M4 16v5h16v-5',
  search: 'M20 20l-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',
  info: 'M12 11v6M12 7v.1M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  check: 'M5 12l4 4L19 6',
  warning: 'M12 8v5M12 17v.1M12 3L2 21h20z',
  chevron: 'M6 9l6 6 6-6',
  close: 'M6 6l12 12M6 18L18 6',
  bars: 'M4 14h3v7H4zM11 9h3v12h-3zM18 3h3v18h-3z',
  people: 'M16 21v-3a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v3M17 14a4 4 0 0 1 4 4v3M14 3a4 4 0 0 1 0 8M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  star: 'M12 3l3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z',
  book: 'M12 5v16M12 5C9 3 5 3 2 4v16c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Z',
} as const

export function Icon({ name, className = '' }: { name: keyof typeof paths; className?: string }) {
  return <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={paths[name]} /></svg>
}
