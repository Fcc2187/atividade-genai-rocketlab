export function Background({ paused }: { paused: boolean }) {
  return <div className={`ambient ${paused ? 'is-paused' : ''}`} aria-hidden="true">
    <svg viewBox="0 0 1440 1000" preserveAspectRatio="none" focusable="false">
      <defs>
        <linearGradient id="ambient-blue" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#5865f2" /><stop offset=".5" stopColor="#243cd8" /><stop offset="1" stopColor="#5865f2" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="ambient-magenta" x1="0" y1="1" x2="1" y2="0">
          <stop stopColor="#ec48bd" stopOpacity="0" /><stop offset=".65" stopColor="#923be5" /><stop offset="1" stopColor="#ec48bd" />
        </linearGradient>
      </defs>
      <path className="ambient-shape shape-blue" fill="url(#ambient-blue)" d="M-240-120H780C560 80 490 155 330 95S60 350-180 370Z" />
      <path className="ambient-shape shape-magenta" fill="url(#ambient-magenta)" d="M1230-200C1000 100 1470 70 1390 440S1140 720 920 950 1450 1280 1610 670V-200Z" />
      <path className="ambient-shape shape-bottom" fill="url(#ambient-blue)" d="M-230 610C50 650 50 860 280 900S1070 810 1570 1010V1250H-230Z" />
    </svg>
  </div>
}
