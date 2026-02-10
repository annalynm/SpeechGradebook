#!/usr/bin/env node
/**
 * Export evaluations from Supabase to the format expected by export_to_jsonl.js.
 * Use this to keep training data updated (run on a schedule: cron, GitHub Actions, etc.).
 *
 * Requires: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY if RLS allows).
 *
 * Usage:
 *   node export_from_supabase.js                    # all evals with transcript (no consent filter)
 *   node export_from_supabase.js --output path.json
 *   node export_from_supabase.js --consent         # only evals where student has consented (data_collection)
 *   node export_from_supabase.js --consent --new-only   # only evals not yet exported for LLM (exported_for_llm_at IS NULL)
 *   node export_from_supabase.js --consent=llm_training   # only evals with llm_training consent (if you use it)
 *
 * Consent: The app uses consent_type = 'data_collection' for student consent (consent links).
 * --new-only: only evaluations where exported_for_llm_at IS NULL (matches dashboard "Export new training data").
 * Without --consent, every evaluation that has transcript and sections is exported (e.g. for first batch).
 *
 * Output: JSON array of { transcript, rubric, scores, source_evaluation_id?, student_hash? }
 * Then:  node export_to_jsonl.js exported.json > train.jsonl
 */

const fs = require('fs');
const path = require('path');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) in the environment.');
  process.exit(1);
}

const args = process.argv.slice(2);
const outIdx = args.indexOf('--output');
const outputPath = outIdx >= 0 && args[outIdx + 1]
  ? args[outIdx + 1]
  : path.join(__dirname, 'exported.json');
const consentArg = args.find((a) => a.startsWith('--consent'));
const consentOnly = consentArg !== undefined;
const consentType = consentArg && consentArg.includes('=')
  ? consentArg.split('=')[1]
  : 'data_collection'; // App uses data_collection for student consent
const newOnly = args.includes('--new-only');

async function fetchSupabase(pathWithQuery) {
  const url = SUPABASE_URL.replace(/\/$/, '') + pathWithQuery;
  const res = await fetch(url, {
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
    },
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`Supabase ${res.status}: ${t}`);
  }
  return res.json();
}

function parseEvalData(ed) {
  if (ed == null) return null;
  if (typeof ed === 'string') {
    try {
      return JSON.parse(ed);
    } catch (_) {
      return null;
    }
  }
  return ed;
}

async function main() {
  // 1) Fetch evaluations that have transcript (and evaluation_data; we filter sections below)
  const select = 'id,transcript,rubric_id,evaluation_data,student_id,course_id';
  let q = `select=${encodeURIComponent(select)}&transcript=not.is.null&order=created_at.desc`;
  if (newOnly) {
    q += '&exported_for_llm_at=is.null';
  }
  let rows = await fetchSupabase(`/rest/v1/evaluations?${q}`);

  if (!Array.isArray(rows)) rows = [];

  // 2) Optionally filter by consent (LLM training)
  if (consentOnly && rows.length > 0) {
    const courseIds = [...new Set(rows.map((r) => r.course_id).filter(Boolean))];
    if (courseIds.length > 0) {
      const consentQuery = `course_id=in.(${courseIds.join(',')})&consent_type=eq.${encodeURIComponent(consentType)}&consent_given=eq.true&select=course_id,student_id`;
      const consentRows = await fetchSupabase(`/rest/v1/consent_forms?${consentQuery}`);
      const consentSet = new Set(
        (Array.isArray(consentRows) ? consentRows : []).map((r) => `${r.course_id}|${r.student_id}`)
      );
      rows = rows.filter((e) => consentSet.has(`${e.course_id}|${e.student_id}`));
      if (rows.length === 0) {
        console.error(`No evaluations with student consent (consent_type=${consentType}) found.`);
        process.exit(0);
      }
    }
  }

  // 3) Build export items: transcript, rubric (name), scores (sections)
  const out = [];
  for (const row of rows) {
    const data = parseEvalData(row.evaluation_data);
    if (!data || !data.sections || typeof data.sections !== 'object') continue;

    const rubricName = data.rubricUsed || row.rubric_id || 'General';
    out.push({
      transcript: row.transcript || '',
      rubric: rubricName,
      scores: data.sections,
      video_notes: (data.video_notes && String(data.video_notes).trim()) || undefined,
      source_evaluation_id: row.id,
      student_hash: row.student_id ? `s_${row.student_id}` : undefined,
    });
  }

  fs.writeFileSync(outputPath, JSON.stringify(out, null, 2), 'utf8');
  console.log(`Wrote ${out.length} evaluations to ${outputPath}`);
  if (out.length > 0) {
    console.log('Next: node export_to_jsonl.js', outputPath, '> train.jsonl');
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
