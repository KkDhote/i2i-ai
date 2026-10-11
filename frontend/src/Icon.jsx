const paths = {
  'arrow-right': <><path d="M4 12h16" /><path d="m14 6 6 6-6 6" /></>,
  'arrow-up': <><path d="M12 20V4" /><path d="m6 10 6-6 6 6" /></>,
  plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>,
  calendar: <><rect x="4" y="5" width="16" height="16" rx="2" /><path d="M8 3v4M16 3v4M4 11h16" /></>,
  chart: <><path d="M4 4v16h16" /><path d="m7 14 4-4 4 2 5-7" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  grid: <><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></>,
  layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5M3 16l9 5 9-5" /></>,
  check: <path d="m5 12 4 4L19 6" />,
  message: <path d="M20 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2v10Z" />,
};

export default function Icon({ name, size = 18, className = '' }) {
  return <svg className={`icon ${className}`.trim()} width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {paths[name] || paths.grid}
  </svg>;
}
