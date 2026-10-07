export default function Header({ title, subtitle, onMenuClick, right }) {
  return (
    <div className="page-header">
      <div>
        <button className="menu-button" onClick={onMenuClick} aria-label="Toggle navigation">
          ☰
        </button>
        <span className="page-title-group">
          <h1>{title}</h1>
          {subtitle && <p className="subtitle">{subtitle}</p>}
        </span>
      </div>
      {right && <div className="page-header-right">{right}</div>}
    </div>
  );
}
