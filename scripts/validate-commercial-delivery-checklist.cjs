#!/usr/bin/env node
"use strict";

const fs = require("fs");

const DEFAULT_PATH = "docs/release/commercial-delivery-checklist.json";
const MANIFEST_STATUSES = new Set(["not_ready", "ready"]);
const ITEM_STATUSES = new Set([
  "complete",
  "complete_until_next_commit",
  "pending_external_input",
  "pending_release_package",
  "pending_device_evidence",
  "pending_final_release",
]);
const STATUSES_REQUIRING_EXTERNAL_HANDOFF = new Set([
  "pending_external_input",
  "pending_release_package",
  "pending_device_evidence",
  "pending_final_release",
]);
const EXTERNAL_HANDOFF_PATH = "docs/release/external-resource-handoff.md";
const EXTERNAL_REQUIREMENTS_PATH = "docs/release/external-resource-requirements.json";

function usage() {
  console.error(
    "Usage: node scripts/validate-commercial-delivery-checklist.cjs [checklist.json]"
  );
}

function fail(message) {
  throw new Error(message);
}

function readStatusField(path) {
  if (!path.endsWith(".md")) return null;
  if (!path.startsWith("docs/release/evidence/")) return null;
  const text = fs.readFileSync(path, "utf8");
  const match = text.match(/^Status:\s*(.+?)\s*$/im);
  return match ? match[1].trim().toLowerCase() : null;
}

function assertNonEmptyString(value, label) {
  if (typeof value !== "string" || value.trim() === "") {
    fail(`${label} must be a non-empty string`);
  }
}

function validateChecklist(path) {
  const manifest = JSON.parse(fs.readFileSync(path, "utf8"));
  if (!MANIFEST_STATUSES.has(manifest.status)) {
    fail(`invalid manifest status: ${manifest.status}`);
  }
  assertNonEmptyString(manifest.objective, "objective");

  if (!Array.isArray(manifest.success_criteria) || manifest.success_criteria.length < 1) {
    fail("success_criteria must be a non-empty array");
  }

  const ids = new Set();
  const nonCompleteItems = [];

  for (const item of manifest.success_criteria) {
    assertNonEmptyString(item.id, "success_criteria[].id");
    if (ids.has(item.id)) {
      fail(`duplicate checklist id: ${item.id}`);
    }
    ids.add(item.id);

    assertNonEmptyString(item.prompt_requirement, `${item.id}.prompt_requirement`);
    assertNonEmptyString(item.current_result, `${item.id}.current_result`);
    if (!ITEM_STATUSES.has(item.status)) {
      fail(`${item.id} has invalid status: ${item.status}`);
    }
    if (item.status !== "complete") {
      nonCompleteItems.push(item.id);
    }

    if (!Array.isArray(item.evidence) || item.evidence.length < 1) {
      fail(`${item.id} must reference at least one evidence artifact`);
    }
    if (!Array.isArray(item.verification) || item.verification.length < 1) {
      fail(`${item.id} must include at least one verification command or evidence step`);
    }
    if (
      STATUSES_REQUIRING_EXTERNAL_HANDOFF.has(item.status) &&
      !item.evidence.includes(EXTERNAL_HANDOFF_PATH)
    ) {
      fail(`${item.id} must reference ${EXTERNAL_HANDOFF_PATH} while status is ${item.status}`);
    }
    if (
      STATUSES_REQUIRING_EXTERNAL_HANDOFF.has(item.status) &&
      !item.evidence.includes(EXTERNAL_REQUIREMENTS_PATH)
    ) {
      fail(`${item.id} must reference ${EXTERNAL_REQUIREMENTS_PATH} while status is ${item.status}`);
    }

    for (const evidencePath of item.evidence) {
      assertNonEmptyString(evidencePath, `${item.id}.evidence[]`);
      if (!fs.existsSync(evidencePath)) {
        fail(`${item.id} references missing evidence artifact: ${evidencePath}`);
      }

      const evidenceStatus = readStatusField(evidencePath);
      if (item.status === "complete" && evidenceStatus && evidenceStatus !== "complete") {
        fail(`${item.id} is complete but ${evidencePath} has Status: ${evidenceStatus}`);
      }
    }
  }

  if (manifest.status === "ready" && nonCompleteItems.length > 0) {
    fail(`manifest is ready but has non-complete criteria: ${nonCompleteItems.join(", ")}`);
  }
  if (manifest.status === "not_ready" && nonCompleteItems.length === 0) {
    fail("manifest is not_ready but all success criteria are complete");
  }

  return {
    path,
    status: manifest.status,
    criteria: manifest.success_criteria.length,
    nonCompleteItems,
  };
}

function main() {
  const args = process.argv.slice(2);
  if (args.length > 1 || args.includes("-h") || args.includes("--help")) {
    usage();
    return args.length > 1 ? 2 : 0;
  }

  try {
    const result = validateChecklist(args[0] || DEFAULT_PATH);
    console.log(
      `Commercial delivery checklist: OK (${result.criteria} criteria, status=${result.status}, non_complete=${result.nonCompleteItems.length})`
    );
    return 0;
  } catch (error) {
    console.error(`Commercial delivery checklist: FAIL - ${error.message}`);
    return 1;
  }
}

if (require.main === module) {
  process.exitCode = main();
}
