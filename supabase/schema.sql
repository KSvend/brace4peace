CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT NOT NULL,
    source_name         TEXT NOT NULL,
    source_url          TEXT NOT NULL,
    source_type         TEXT NOT NULL CHECK (source_type IN (
                            'UN_AGENCY', 'REGIONAL_BODY', 'THINK_TANK',
                            'QUALITY_MEDIA', 'ACADEMIC', 'NGO_CSO',
                            'FACT_CHECKER')),
    date_published      DATE,
    country             TEXT[],
    theme               TEXT[],
    classification      TEXT,
    credibility_score   REAL CHECK (credibility_score BETWEEN 0 AND 1),
    summary             TEXT,
    fetch_status        TEXT DEFAULT 'PENDING' CHECK (fetch_status IN (
                            'PENDING', 'FETCHED', 'FAILED', 'PAYWALLED')),
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID REFERENCES sources(id),
    tier            TEXT NOT NULL CHECK (tier IN ('full_text', 'finding', 'event')),
    content         TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    embedding       vector(384),
    country         TEXT[],
    theme           TEXT[],
    classification  TEXT CHECK (classification IN ('CONTEXT', 'HS_DISINFO', 'VE_PROPAGANDA')),
    date_published  DATE,
    verified        BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding ON document_chunks
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_country ON document_chunks USING GIN (country);
CREATE INDEX idx_chunks_theme ON document_chunks USING GIN (theme);
CREATE INDEX idx_chunks_tier ON document_chunks(tier);
CREATE INDEX idx_chunks_verified ON document_chunks(verified);

CREATE TABLE findings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id           UUID REFERENCES sources(id),
    title               TEXT NOT NULL,
    summary             TEXT NOT NULL,
    country             TEXT[] NOT NULL,
    theme               TEXT[] NOT NULL,
    classification      TEXT NOT NULL CHECK (classification IN (
                            'CONTEXT', 'HS_DISINFO', 'VE_PROPAGANDA')),
    hs_subtype          TEXT,
    confidence          REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    status              TEXT NOT NULL DEFAULT 'UNVERIFIED' CHECK (status IN (
                            'UNVERIFIED', 'VERIFIED', 'FLAGGED', 'REJECTED')),
    verified_by         TEXT,
    verified_at         TIMESTAMP,
    verification_note   TEXT,
    created_by          TEXT NOT NULL,
    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_country ON findings USING GIN (country);

CREATE TABLE verification_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id      UUID NOT NULL REFERENCES findings(id),
    reviewer_id     TEXT NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('VERIFY', 'FLAG', 'REJECT')),
    note            TEXT,
    previous_status TEXT NOT NULL,
    new_status      TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE post_annotations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id         TEXT NOT NULL,
    reviewer        TEXT NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('CONFIRM', 'CORRECT', 'FLAG')),
    corrections     JSONB,
    note            TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_annotations_post ON post_annotations(post_id);

CREATE TABLE aggregated_stats (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stat_type       TEXT NOT NULL,
    country         TEXT,
    period          TEXT,
    data            JSONB NOT NULL,
    computed_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      TEXT NOT NULL,
    query_text      TEXT NOT NULL,
    query_language  TEXT,
    filters         JSONB,
    response_text   TEXT,
    sources_cited   JSONB,
    confidence      TEXT,
    feedback        TEXT,
    response_time_ms INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_session ON chat_sessions(session_id);

CREATE TABLE system_metadata (
    key             TEXT PRIMARY KEY,
    value           JSONB NOT NULL,
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Vector similarity search function
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(384),
    match_count int DEFAULT 10,
    filter_country text DEFAULT NULL,
    filter_theme text DEFAULT NULL,
    filter_verified_only boolean DEFAULT false
)
RETURNS TABLE (
    id uuid,
    source_id uuid,
    tier text,
    content text,
    country text[],
    theme text[],
    classification text,
    date_published date,
    verified boolean,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id, dc.source_id, dc.tier, dc.content,
        dc.country, dc.theme, dc.classification,
        dc.date_published, dc.verified,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE
        (filter_country IS NULL OR filter_country = ANY(dc.country))
        AND (filter_theme IS NULL OR filter_theme = ANY(dc.theme))
        AND (NOT filter_verified_only OR dc.verified = true)
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
