CREATE TABLE IF NOT EXISTS subject_aliases (
    owner TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    alias_folded TEXT NOT NULL,
    PRIMARY KEY (owner, subject_id, alias_folded),
    FOREIGN KEY (owner, subject_id) REFERENCES subjects(owner, id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_subject_aliases_owner_folded
    ON subject_aliases(owner, alias_folded);
