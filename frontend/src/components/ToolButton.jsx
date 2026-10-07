export default function ToolButton({ tool, onClick, disabled, used }) {
  return (
    <button className={`tool-button ${used ? "used" : ""}`} onClick={() => onClick(tool)} disabled={disabled}>
      <span className="tool-button-name">{tool.display_name}</span>
      <span className="tool-button-desc">{tool.description}</span>
    </button>
  );
}
