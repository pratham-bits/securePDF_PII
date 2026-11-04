import { entityLabel, TIER_ORDER, TIER_TITLES } from "../lib/entities.js";
import "./FindingsPanel.css";

const LOW_CONFIDENCE = 0.6;

export default function FindingsPanel({
  findings,
  selectedId,
  busyId,
  locked,
  onSelect,
  onToggle,
  onRemove,
}) {
  if (findings.length === 0) {
    return (
      <p className="panel__empty">
        Nothing was detected automatically. Detection is never perfect, so check
        every page yourself and add boxes where needed.
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
              const busy = finding.id === busyId;
              const isManual = finding.source === "user";
              return (
                <li
                  key={finding.id}
                  className={`panel__row${selected ? " panel__row--selected" : ""}`}
                >
                  <button
                    type="button"
                    className="panel__item"
                    onClick={() => onSelect(finding.id, true)}
                  >
                    <span className="panel__name">
                      {entityLabel(finding.entity_type)}
                    </span>
                    <span className="panel__meta">
                      page {finding.page + 1}
                      {finding.decision === "keep" && " · kept visible"}
                    </span>
                    {finding.score < LOW_CONFIDENCE && (
                      <span className="panel__warn">
                        Low confidence: please check
                      </span>
                    )}
                  </button>
                  <div className="panel__controls">
                    {isManual ? (
                      <button
                        type="button"
                        className="btn btn--small btn--danger"
                        disabled={busy || locked}
                        onClick={() => onRemove(finding)}
                      >
                        Delete
                      </button>
                    ) : (
                      <label className="panel__check">
                        <input
                          type="checkbox"
                          checked={finding.decision === "redact"}
                          disabled={busy || locked}
                          onChange={() => onToggle(finding)}
                        />
                        Redact
                      </label>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
