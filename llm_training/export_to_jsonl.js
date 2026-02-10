#!/usr/bin/env node
/**
 * Convert SpeechGradebook LLM training export (JSON) to JSONL with messages format
 * for instruction tuning (system / user / assistant).
 *
 * Usage:
 *   node export_to_jsonl.js exported.json > train.jsonl
 *   node export_to_jsonl.js exported.json --split 0.9   # writes train.jsonl + validation.jsonl
 *
 * Input: JSON array of { transcript, rubric, scores, markers?, student_hash?, institution_hash? }
 * Output: One JSON object per line with { messages: [ { role, content }, ... ] }
 */

const fs = require('fs');
const path = require('path');

function buildSystemPrompt(rubricName) {
  return (
    'You are a speech evaluator. Apply the given rubric and output scores and comments as a single JSON object. ' +
    'The JSON must match the rubric structure: for each category, include "score", "maxScore", and "subcategories" (array of { "name", "points", "maxPoints" }). ' +
    'Do not include any explanation outside the JSON.'
  );
}

/** Format rubric structure for the prompt: categories and subcategories so the model knows exactly what to output. */
function formatRubricStructure(rubricStructure) {
  if (!rubricStructure || !rubricStructure.categories || !Array.isArray(rubricStructure.categories)) return null;
  const lines = [];
  for (const cat of rubricStructure.categories) {
    const name = typeof cat === 'object' && cat !== null ? cat.name : String(cat);
    const subs = (typeof cat === 'object' && cat !== null && Array.isArray(cat.subcategories))
      ? cat.subcategories
      : [];
    const subList = subs.map((s) => (typeof s === 'string' ? s : (s && s.name) || '')).filter(Boolean);
    if (subList.length) lines.push(`- ${name}: ${subList.join(', ')}`);
    else lines.push(`- ${name}`);
  }
  return lines.length ? lines.join('\n') : null;
}

function buildUserPrompt(transcript, rubricName, markers, videoNotes, rubricStructure) {
  let user = `Rubric: ${rubricName}\n`;
  const structureText = formatRubricStructure(rubricStructure);
  if (structureText) {
    user += 'Categories and subcategories to score:\n' + structureText + '\n\n';
  }
  user += 'Transcript:\n' + (transcript || '');
  if (videoNotes && String(videoNotes).trim()) {
    user += '\n\nVideo notes (visual delivery):\n' + String(videoNotes).trim();
  }
  if (markers && Array.isArray(markers) && markers.length > 0) {
    user += '\n\nTimeline markers (optional): ' + JSON.stringify(markers);
  }
  return user;
}

function buildAssistantContent(scores) {
  if (typeof scores !== 'object' || scores === null) return '{}';
  return JSON.stringify(scores);
}

function exportToJsonl(items) {
  const out = [];
  for (const item of items) {
    const system = buildSystemPrompt(item.rubric || 'General');
    const user = buildUserPrompt(
      item.transcript,
      item.rubric,
      item.markers,
      item.video_notes,
      item.rubric_structure
    );
    const assistant = buildAssistantContent(item.scores);
    out.push({
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user },
        { role: 'assistant', content: assistant },
      ],
    });
  }
  return out;
}

function deterministicSplit(items, trainFraction, hashKey = 'student_hash') {
  const keyToItems = new Map();
  for (const item of items) {
    const k = item[hashKey] ?? item.source_evaluation_id ?? item.student_hash ?? `rand-${Math.random()}`;
    const key = String(k);
    if (!keyToItems.has(key)) keyToItems.set(key, []);
    keyToItems.get(key).push(item);
  }
  const keys = [...keyToItems.keys()].sort();
  const nTrain = Math.max(1, Math.floor(keys.length * trainFraction));
  const trainKeySet = new Set(keys.slice(0, nTrain));
  const train = [];
  const valid = [];
  for (const item of items) {
    const k = item[hashKey] ?? item.source_evaluation_id ?? item.student_hash ?? '';
    if (trainKeySet.has(String(k))) train.push(item);
    else valid.push(item);
  }
  return { train, validation: valid };
}

function main() {
  const args = process.argv.slice(2);
  const splitIdx = args.indexOf('--split');
  const splitArg = args.find((a) => a.startsWith('--split=')) ?? (splitIdx >= 0 ? args[splitIdx + 1] : null);
  const trainFraction = splitArg != null ? parseFloat(splitArg.replace('--split=', '')) : null;
  const fileArg = args.find((a) => !a.startsWith('--') && !a.startsWith('-'));
  if (!fileArg) {
    console.error('Usage: node export_to_jsonl.js <exported.json> [--split 0.9]');
    process.exit(1);
  }
  const raw = fs.readFileSync(fileArg, 'utf8');
  let items;
  try {
    items = JSON.parse(raw);
  } catch (e) {
    console.error('Invalid JSON:', e.message);
    process.exit(1);
  }
  if (!Array.isArray(items)) items = [items];

  const baseDir = path.dirname(fileArg);

  if (trainFraction != null && trainFraction > 0 && trainFraction < 1) {
    const { train, validation } = deterministicSplit(items, trainFraction);
    const trainLines = exportToJsonl(train);
    const validLines = exportToJsonl(validation);
    const trainPath = path.join(baseDir, 'train.jsonl');
    const validPath = path.join(baseDir, 'validation.jsonl');
    fs.writeFileSync(trainPath, trainLines.map((o) => JSON.stringify(o)).join('\n') + '\n');
    fs.writeFileSync(validPath, validLines.map((o) => JSON.stringify(o)).join('\n') + '\n');
    console.error(`Wrote ${trainLines.length} examples to ${trainPath}`);
    console.error(`Wrote ${validLines.length} examples to ${validPath}`);
    return;
  }

  const lines = exportToJsonl(items);
  for (const obj of lines) {
    console.log(JSON.stringify(obj));
  }
}

main();
