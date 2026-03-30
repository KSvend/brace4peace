"use client";

import { useState, useEffect, useCallback } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface BlindPost {
  i: string;   // post ID
  t: string;   // text
  d: string;   // date
  c: string;   // country
  p: string;   // platform
}

type Classification = "Normal" | "Abusive" | "Hate";
type Confidence = "Low" | "Medium" | "High";

const SUBTYPES = [
  "Ethnic Targeting",
  "Clan Targeting",
  "Political Incitement",
  "Religious Incitement",
  "Dehumanisation",
  "Anti-Foreign",
  "General Abuse",
  "Gendered Violence",
] as const;

type Subtype = (typeof SUBTYPES)[number];

interface AnnotationState {
  classification: Classification | null;
  subtype: Subtype | "";
  confidence: Confidence | null;
  note: string;
  submitted: boolean;
  submitting: boolean;
  error: string | null;
}

const CLASS_COLORS: Record<Classification, { bg: string; ring: string; label: string }> = {
  Normal:  { bg: "#3BAA7F", ring: "#2e8f69", label: "Normal" },
  Abusive: { bg: "#E07B39", ring: "#c0652a", label: "Abusive" },
  Hate:    { bg: "#D05454", ring: "#b03e3e", label: "Hate" },
};

const CONF_LABELS: Confidence[] = ["Low", "Medium", "High"];

// ─── Login Screen ─────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }: { onLogin: (name: string) => void }) {
  const [name, setName] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    localStorage.setItem("iris_reviewer", trimmed);
    onLogin(trimmed);
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "var(--bg-primary, #0f1117)" }}
    >
      <div
        className="w-full max-w-sm rounded-lg border p-8 space-y-6"
        style={{
          background: "var(--surface, #1a1d23)",
          borderColor: "var(--border-subtle, #2a2d35)",
        }}
      >
        <div className="space-y-1">
          <h1
            className="text-xl font-semibold"
            style={{ color: "var(--text-primary, #f0f0ee)" }}
          >
            IRIS Blind Annotation
          </h1>
          <p
            className="text-[13px]"
            style={{ color: "var(--text-muted, #888884)" }}
          >
            Enter your reviewer ID to begin annotating posts.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label
              htmlFor="reviewer"
              className="block text-[12px] font-medium uppercase tracking-[0.05em]"
              style={{ color: "var(--text-muted, #888884)" }}
            >
              Reviewer ID
            </label>
            <input
              id="reviewer"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. annotator_kenya"
              autoFocus
              className="w-full rounded-md border px-3 py-2 text-[14px] outline-none transition-all"
              style={{
                background: "var(--surface-muted, #141619)",
                borderColor: "var(--border-subtle, #2a2d35)",
                color: "var(--text-primary, #f0f0ee)",
              }}
              onFocus={(e) =>
                (e.currentTarget.style.borderColor = "var(--accent, #8071BC)")
              }
              onBlur={(e) =>
                (e.currentTarget.style.borderColor =
                  "var(--border-subtle, #2a2d35)")
              }
            />
          </div>
          <button
            type="submit"
            disabled={!name.trim()}
            className="w-full rounded-md px-4 py-2.5 text-[13px] font-medium transition-opacity disabled:opacity-40"
            style={{
              background: "var(--accent, #8071BC)",
              color: "#fff",
            }}
          >
            Start Annotating
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── Annotation Card ──────────────────────────────────────────────────────────

function AnnotationCard({
  post,
  reviewer,
  onDone,
}: {
  post: BlindPost;
  reviewer: string;
  onDone: () => void;
}) {
  const [ann, setAnn] = useState<AnnotationState>({
    classification: null,
    subtype: "",
    confidence: null,
    note: "",
    submitted: false,
    submitting: false,
    error: null,
  });

  const needsSubtype =
    ann.classification === "Abusive" || ann.classification === "Hate";

  const canSubmit =
    ann.classification !== null &&
    ann.confidence !== null &&
    (!needsSubtype || ann.subtype !== "") &&
    !ann.submitted &&
    !ann.submitting;

  async function handleSubmit() {
    if (!canSubmit) return;
    setAnn((a) => ({ ...a, submitting: true, error: null }));

    try {
      const res = await fetch("/api/annotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          post_id: post.i,
          reviewer_name: reviewer,
          pass_number: 1,
          classification: ann.classification,
          subtype: ann.subtype || null,
          confidence: ann.confidence,
          note: ann.note || null,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }

      setAnn((a) => ({ ...a, submitted: true, submitting: false }));
      onDone();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      setAnn((a) => ({ ...a, submitting: false, error: msg }));
    }
  }

  if (ann.submitted) {
    return (
      <div
        className="rounded-md border px-4 py-3 flex items-center gap-3"
        style={{
          borderColor: "var(--border-subtle, #2a2d35)",
          background: "var(--surface-muted, #141619)",
          opacity: 0.6,
        }}
      >
        <span style={{ color: "#3BAA7F", fontSize: 18 }}>✓</span>
        <span
          className="text-[13px]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          Annotated as{" "}
          <strong style={{ color: CLASS_COLORS[ann.classification!].bg }}>
            {ann.classification}
          </strong>
          {ann.subtype ? ` · ${ann.subtype}` : ""} · {ann.confidence} confidence
        </span>
      </div>
    );
  }

  return (
    <div
      className="rounded-md border space-y-4 px-4 py-4"
      style={{
        borderColor: "var(--border-subtle, #2a2d35)",
        background: "var(--surface, #1a1d23)",
      }}
    >
      {/* Post metadata */}
      <div className="flex items-center gap-3 flex-wrap">
        <span
          className="text-[11px] font-medium uppercase tracking-[0.04em]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          {post.p}
        </span>
        <span
          className="text-[11px]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          ·
        </span>
        <span
          className="text-[11px]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          {post.c}
        </span>
        <span
          className="text-[11px]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          ·
        </span>
        <span
          className="text-[11px] tabular-nums"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          {post.d ? post.d.slice(0, 10) : "—"}
        </span>
      </div>

      {/* Post text */}
      <p
        className="text-[14px] leading-relaxed"
        style={{ color: "var(--text-primary, #f0f0ee)" }}
      >
        {post.t}
      </p>

      {/* Classification buttons */}
      <div className="space-y-1.5">
        <div
          className="text-[11px] font-medium uppercase tracking-[0.04em]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          Classification
        </div>
        <div className="flex gap-2 flex-wrap">
          {(["Normal", "Abusive", "Hate"] as Classification[]).map((cls) => {
            const isSelected = ann.classification === cls;
            const colors = CLASS_COLORS[cls];
            return (
              <button
                key={cls}
                onClick={() =>
                  setAnn((a) => ({
                    ...a,
                    classification: cls,
                    subtype: cls === "Normal" ? "" : a.subtype,
                  }))
                }
                className="rounded-md px-4 py-1.5 text-[13px] font-medium border transition-all"
                style={{
                  background: isSelected ? colors.bg : "transparent",
                  borderColor: isSelected ? colors.ring : "var(--border-subtle, #2a2d35)",
                  color: isSelected ? "#fff" : colors.bg,
                }}
              >
                {colors.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Subtype dropdown — only when Abusive or Hate */}
      {needsSubtype && (
        <div className="space-y-1.5">
          <div
            className="text-[11px] font-medium uppercase tracking-[0.04em]"
            style={{ color: "var(--text-muted, #888884)" }}
          >
            Subtype
          </div>
          <select
            value={ann.subtype}
            onChange={(e) =>
              setAnn((a) => ({ ...a, subtype: e.target.value as Subtype | "" }))
            }
            className="rounded-md border px-3 py-2 text-[13px] outline-none w-full max-w-xs"
            style={{
              background: "var(--surface-muted, #141619)",
              borderColor: "var(--border-subtle, #2a2d35)",
              color: ann.subtype
                ? "var(--text-primary, #f0f0ee)"
                : "var(--text-muted, #888884)",
            }}
          >
            <option value="">— select subtype —</option>
            {SUBTYPES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Confidence toggle */}
      <div className="space-y-1.5">
        <div
          className="text-[11px] font-medium uppercase tracking-[0.04em]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          Confidence
        </div>
        <div className="flex gap-2">
          {CONF_LABELS.map((lvl) => {
            const isSelected = ann.confidence === lvl;
            return (
              <button
                key={lvl}
                onClick={() => setAnn((a) => ({ ...a, confidence: lvl }))}
                className="rounded-md px-4 py-1.5 text-[13px] font-medium border transition-all"
                style={{
                  background: isSelected
                    ? "var(--accent, #8071BC)"
                    : "transparent",
                  borderColor: isSelected
                    ? "var(--accent, #8071BC)"
                    : "var(--border-subtle, #2a2d35)",
                  color: isSelected
                    ? "#fff"
                    : "var(--text-secondary, #b0b0ac)",
                }}
              >
                {lvl}
              </button>
            );
          })}
        </div>
      </div>

      {/* Optional note */}
      <div className="space-y-1.5">
        <div
          className="text-[11px] font-medium uppercase tracking-[0.04em]"
          style={{ color: "var(--text-muted, #888884)" }}
        >
          Note{" "}
          <span style={{ textTransform: "none", fontWeight: 400 }}>
            (optional)
          </span>
        </div>
        <textarea
          value={ann.note}
          onChange={(e) => setAnn((a) => ({ ...a, note: e.target.value }))}
          placeholder="Any observations about this post…"
          rows={2}
          className="w-full rounded-md border px-3 py-2 text-[13px] outline-none resize-none transition-all"
          style={{
            background: "var(--surface-muted, #141619)",
            borderColor: "var(--border-subtle, #2a2d35)",
            color: "var(--text-primary, #f0f0ee)",
          }}
          onFocus={(e) =>
            (e.currentTarget.style.borderColor = "var(--accent, #8071BC)")
          }
          onBlur={(e) =>
            (e.currentTarget.style.borderColor = "var(--border-subtle, #2a2d35)")
          }
        />
      </div>

      {/* Error */}
      {ann.error && (
        <div
          className="text-[12px] rounded-md px-3 py-2"
          style={{ background: "#D054541a", color: "#D05454" }}
        >
          Error: {ann.error}
        </div>
      )}

      {/* Submit */}
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="rounded-md px-5 py-2 text-[13px] font-medium transition-opacity disabled:opacity-35"
          style={{ background: "var(--accent, #8071BC)", color: "#fff" }}
        >
          {ann.submitting ? "Submitting…" : "Submit Annotation"}
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AnnotatePage() {
  const [reviewer, setReviewer] = useState<string | null>(null);
  const [posts, setPosts] = useState<BlindPost[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [doneIds, setDoneIds] = useState<Set<string>>(new Set());

  // Restore reviewer from localStorage
  useEffect(() => {
    const stored = localStorage.getItem("iris_reviewer");
    if (stored) setReviewer(stored);
  }, []);

  const fetchPosts = useCallback(
    async (rev: string, off: number) => {
      setLoading(true);
      setLoadError(null);
      try {
        const res = await fetch(
          `/api/annotate?reviewer=${encodeURIComponent(rev)}&limit=20&offset=${off}`
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setPosts((prev) => (off === 0 ? data.posts : [...prev, ...data.posts]));
        setTotal(data.total ?? 0);
        setOffset(off + data.posts.length);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load posts";
        setLoadError(msg);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Load posts when reviewer is set
  useEffect(() => {
    if (reviewer) fetchPosts(reviewer, 0);
  }, [reviewer, fetchPosts]);

  function handleLogin(name: string) {
    setReviewer(name);
  }

  function handleLogout() {
    localStorage.removeItem("iris_reviewer");
    setReviewer(null);
    setPosts([]);
    setOffset(0);
    setDoneIds(new Set());
  }

  function markDone(postId: string) {
    setDoneIds((prev) => new Set([...prev, postId]));
  }

  if (!reviewer) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  const annotatedCount = doneIds.size;

  return (
    <div
      className="min-h-screen"
      style={{ background: "var(--bg-primary, #0f1117)" }}
    >
      {/* Top bar */}
      <div
        className="sticky top-0 z-10 border-b px-6 py-3 flex items-center justify-between"
        style={{
          background: "var(--surface, #1a1d23)",
          borderColor: "var(--border-subtle, #2a2d35)",
        }}
      >
        <div className="flex items-center gap-4">
          <span
            className="text-[13px] font-semibold tracking-tight"
            style={{ color: "var(--text-primary, #f0f0ee)" }}
          >
            IRIS · Blind Annotation
          </span>
          <span
            className="text-[12px] tabular-nums px-2.5 py-0.5 rounded-full"
            style={{
              background: "var(--surface-muted, #141619)",
              color: "var(--text-muted, #888884)",
            }}
          >
            {annotatedCount} of {total} annotated
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className="text-[12px]"
            style={{ color: "var(--text-muted, #888884)" }}
          >
            {reviewer}
          </span>
          <button
            onClick={handleLogout}
            className="text-[12px] rounded-md px-3 py-1 border transition-all"
            style={{
              borderColor: "var(--border-subtle, #2a2d35)",
              color: "var(--text-muted, #888884)",
            }}
          >
            Switch reviewer
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-4">
        {/* Load error */}
        {loadError && (
          <div
            className="rounded-md px-4 py-3 text-[13px]"
            style={{ background: "#D054541a", color: "#D05454" }}
          >
            Failed to load posts: {loadError}
          </div>
        )}

        {/* Empty state */}
        {!loading && posts.length === 0 && !loadError && (
          <div
            className="text-center py-16 text-[14px]"
            style={{ color: "var(--text-muted, #888884)" }}
          >
            No posts in queue for <strong>{reviewer}</strong>.
          </div>
        )}

        {/* Post cards */}
        {posts.map((post) =>
          doneIds.has(post.i) ? (
            <AnnotationCard
              key={post.i}
              post={post}
              reviewer={reviewer}
              onDone={() => markDone(post.i)}
            />
          ) : (
            <AnnotationCard
              key={post.i}
              post={post}
              reviewer={reviewer}
              onDone={() => markDone(post.i)}
            />
          )
        )}

        {/* Load more */}
        {posts.length > 0 && posts.length < total && (
          <div className="flex justify-center pt-4">
            <button
              onClick={() => fetchPosts(reviewer, offset)}
              disabled={loading}
              className="rounded-md border px-6 py-2.5 text-[13px] font-medium transition-all disabled:opacity-40"
              style={{
                borderColor: "var(--border-subtle, #2a2d35)",
                color: "var(--text-secondary, #b0b0ac)",
                background: "var(--surface, #1a1d23)",
              }}
            >
              {loading ? "Loading…" : `Load more (${total - posts.length} remaining)`}
            </button>
          </div>
        )}

        {/* Loading indicator for initial load */}
        {loading && posts.length === 0 && (
          <div
            className="text-center py-16 text-[13px]"
            style={{ color: "var(--text-muted, #888884)" }}
          >
            Loading posts…
          </div>
        )}
      </div>
    </div>
  );
}
