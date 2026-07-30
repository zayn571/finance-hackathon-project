import workingFiles from "../data/workingFiles.json";

/** Links to the real source workbooks in Google Drive. */
export default function WorkingFiles() {
  return (
    <div className="card panel-tint">
      <div className="card-header">
        <div>
          <h2>Working files</h2>
          <p className="hint">The source workbooks behind these numbers, in Google Drive.</p>
        </div>
      </div>
      {workingFiles.groups.map((g) => (
        <div key={g.kind} className="wf-group">
          <h3 className="sub-head">{g.label}</h3>
          <div className="wf-grid">
            {g.files.map((f) => (
              <a key={f.url} className="wf-card" href={f.url} target="_blank" rel="noreferrer">
                <span className={g.kind === "excel" ? "wf-icon excel" : "wf-icon sheets"} aria-hidden="true" />
                <span className="wf-body">
                  <span className="wf-name">{f.name}</span>
                  <span className="wf-meta">{f.meta}</span>
                </span>
              </a>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
