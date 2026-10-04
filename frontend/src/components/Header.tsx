type Props = {
  theme: 'light' | 'dark'
  onToggleTheme: () => void
  onOpenHistory: () => void
  onOpenHelp: () => void
}

export default function Header({ theme, onToggleTheme, onOpenHistory, onOpenHelp }: Props) {
  const themeLabel = theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro'
  return <header className="header">
    <div className="brand" aria-label="CineData">
      <img src={`/brand/logo-${theme}.png`} alt="" width="40" height="40" />
      <span>cinedata</span>
    </div>
    <p className="tagline">ANALYTICS / CINEMA EM PERSPECTIVA</p>
    <div className="header-actions">
      <button className="desktop-help secondary" onClick={onOpenHelp}>Como usar</button>
      <button className="mobile-history secondary" onClick={onOpenHistory}>Histórico</button>
      <button className="theme-toggle secondary" onClick={onToggleTheme} aria-label={themeLabel} title={themeLabel}>
        <img src={`/icons/${theme === 'light' ? 'moon' : 'sun'}.svg`} width="24" height="24" alt="" />
      </button>
    </div>
  </header>
}
