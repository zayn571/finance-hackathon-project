import { useState } from "react";
import board from "../data/closeBoard.json";

const AVATAR_COLOR: Record<string, string> = {
  VP: "#0B2D4C",
  ER: "#09838D",
  ZM: "#00A5A2",
};

/**
 * Month-end close board, backed by the real Asana project. Completion state is
 * read from Asana; toggling a checkbox here is local to the page and does not
 * write back to Asana.
 */
export default function CloseBoard() {
  const [done, setDone] = useState<Record<string, boolean>>(
    Object.fromEntries(board.tasks.map((t) => [t.id, t.done]))
  );
  const [delegated, setDelegated] = useState<Record<string, boolean>>({});

  const completeCount = board.tasks.filter((t) => done[t.id]).length;
  const progress = Math.round((completeCount / board.total) * 100);

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="eyebrow eyebrow-teal">Team board</div>
          <h2>{board.project}</h2>
          <p className="hint">
            {completeCount} of {board.total} tasks complete. Live from{" "}
            <a href={board.asanaUrl} target="_blank" rel="noreferrer">Asana</a>. Checking a box
            here is local to this page — it does not write back to Asana.
          </p>
        </div>
        <div className="member-chips">
          {board.members.map((m) => (
            <span key={m.initials} className="member-chip">
              <span className="avatar" style={{ background: AVATAR_COLOR[m.initials] }}>
                {m.initials}
              </span>
              <span className="member-body">
                <span className="member-name">{m.name}</span>
                <span className="member-role">{m.role}</span>
              </span>
            </span>
          ))}
        </div>
      </div>

      <div className="progress-track">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <div className="table-scroll">
        <table className="close-table">
          <thead>
            <tr>
              <th style={{ width: 28 }} />
              <th className="label-col">Task</th>
              <th style={{ width: 150 }}>Assignee</th>
              <th style={{ width: 70 }}>BD due</th>
              <th style={{ width: 96 }}>Due date</th>
            </tr>
          </thead>
          <tbody>
            {board.tasks.map((t) => {
              const isDone = done[t.id];
              return (
                <tr key={t.id} className="is-row">
                  <td>
                    <button
                      className={isDone ? "check checked" : "check"}
                      aria-label={isDone ? `Mark ${t.name} not done` : `Mark ${t.name} done`}
                      aria-pressed={isDone}
                      onClick={() => setDone((s) => ({ ...s, [t.id]: !s[t.id] }))}
                    >
                      {isDone ? "✓" : ""}
                    </button>
                  </td>
                  <td className="label-col">
                    <span className={isDone ? "task-name done" : "task-name"}>{t.name}</span>
                    {t.skill && (
                      <>
                        <span className={delegated[t.id] ? "badge badge-teal mono" : "badge badge-tint mono"}>
                          {t.skill}
                        </span>
                        <button
                          className={delegated[t.id] ? "btn btn-ghost assigned" : "btn btn-ghost"}
                          onClick={() => setDelegated((s) => ({ ...s, [t.id]: !s[t.id] }))}
                        >
                          {delegated[t.id] ? "Agent assigned" : "Delegate to agent"}
                        </button>
                      </>
                    )}
                  </td>
                  <td className="assignee-cell">
                    <span className="avatar sm" style={{ background: AVATAR_COLOR[t.initials] }}>
                      {t.initials}
                    </span>
                    {t.assignee}
                  </td>
                  <td>{t.bd > 0 ? `+${t.bd}` : t.bd}</td>
                  <td className={t.bd > 0 ? "post-close" : ""}>{t.due.slice(5)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
