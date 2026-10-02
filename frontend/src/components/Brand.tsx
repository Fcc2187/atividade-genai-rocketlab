import { useId } from 'react'

export function BrandMark({ className = '' }: { className?: string }) {
  const id = useId()
  return <svg className={`brand-symbol ${className}`} viewBox="0 0 80 80" aria-hidden="true" focusable="false">
    <defs><linearGradient id={`${id}-blue`} x1="0" x2="1" y1="0" y2="1"><stop stopColor="#78c6ff" /><stop offset="1" stopColor="#5865f2" /></linearGradient>
      <linearGradient id={`${id}-pink`} x1="0" x2="0" y1="0" y2="1"><stop stopColor="#f7a5ea" /><stop offset="1" stopColor="#ec48bd" /></linearGradient></defs>
    <path d="M38 10a28 28 0 1 0 0 56V47h17a28 28 0 0 0-17-37Z" fill={`url(#${id}-blue)`} />
    <g fill="#101443"><circle cx="35" cy="21" r="5" /><circle cx="21" cy="30" r="5" /><circle cx="20" cy="46" r="5" /><circle cx="34" cy="55" r="5" /><circle cx="46" cy="31" r="5" /><circle cx="33" cy="38" r="3" /></g>
    <rect x="40" y="51" width="9" height="23" rx="1.5" fill={`url(#${id}-blue)`} /><rect x="53" y="39" width="9" height="35" rx="1.5" fill={`url(#${id}-blue)`} /><rect x="66" y="27" width="9" height="47" rx="1.5" fill={`url(#${id}-pink)`} />
  </svg>
}

export function Brand() {
  return <div className="brand"><BrandMark /><span><strong>CineData</strong><span className="brand-subtitle">Analytics</span></span></div>
}
