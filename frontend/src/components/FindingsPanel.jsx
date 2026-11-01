import { entityLabel, TIER_ORDER, TIER_TITLES } from "../lib/entities.js";
import "./FindingsPanel.css";

const LOW_CONFIDENCE = 0.6;

export default function FindingsPanel({ findings, selectedId, onSelect }) {
  if (findings.length === 0) {
    return (
      <p className="panel__empty">
        Nothing was detected automatically. Detection is never perfect, so check
        every page yourself.
      </p>
    );
  }

  const groups = TIER_ORDER.map((tier) => ({
    tier,
    items: findings.filter((finding) => finding.tier === tier),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="panel">
      {groups.map((group) => (
        <section key={group.tier} className="panel__group">
          <h3 className="panel__heading">{TIER_TITLES[group.tier]}</h3>
          <ul className="panel__list">
            {group.items.map((finding) => {
              const selected = finding.id === selectedId;
              return (
                <li key={finding.id}>
                  <button
                    type="button"
                    className={`panel__item${selected ? " panel__item--selected" : ""}`}
                    onClick={() => onSelect(finding.id, true)}
                  >
                    <span className="panel__name">
                      {entityLabel(finding.entity_type)}
                    </span>
                    <span className="panel__meta">
                      page {finding.page + 1} ·{" "}
                      {finding.decision === "redact"
                        ? "will be redacted"
                        : "kept"}
                    </span>
                    {finding.score < LOW_CONFIDENCE && (
                      <span className="panel__warn">
                        Low confidence: please check
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
