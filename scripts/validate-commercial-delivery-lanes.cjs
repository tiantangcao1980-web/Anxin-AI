#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const repoRoot = path.resolve(__dirname, "..");
const manifestPath = path.join(repoRoot, "docs", "release", "commercial-delivery-lanes.json");

const allowedTopStatuses = new Set(["not_ready", "ready"]);
const allowedLaneStatuses = new Set([
  "complete",
  "in_progress",
  "ready_to_run",
  "pending_external_input",
  "pending_device_evidence",
  "pending_final_release",
]);
const statusesRequiringExternalInput = new Set([
  "pending_external_input",
  "pending_device_evidence",
  "pending_final_release",
]);
const externalHandoffPath = "docs/release/external-resource-handoff.md";
const externalRequirementsPath = "docs/release/external-resource-requirements.json";

function fail(message, failures) {
  failures.push(message);
}

function readJson(filePath, failures) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    fail(`cannot read or parse ${path.relative(repoRoot, filePath)}: ${error.message}`, failures);
    return null;
  }
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function requireStringArray(lane, key, failures) {
  const value = lane[key];
  if (!Array.isArray(value) || value.length === 0) {
    fail(`lane ${lane.id || "<missing-id>"} must have a non-empty ${key} array`, failures);
    return [];
  }
  for (const item of value) {
    if (!isNonEmptyString(item)) {
      fail(`lane ${lane.id || "<missing-id>"} has an empty ${key} item`, failures);
    }
  }
  return value;
}

function evidenceStatus(relativePath) {
  if (!relativePath.startsWith("docs/release/evidence/") || !relativePath.endsWith(".md")) {
    return null;
  }
  const fullPath = path.join(repoRoot, relativePath);
  if (!fs.existsSync(fullPath)) {
    return null;
  }
  const match = fs.readFileSync(fullPath, "utf8").match(/^Status:\s*(\S+)/m);
  return match ? match[1] : null;
}

function validateManifest(manifest) {
  const failures = [];

  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) {
    fail("manifest must be a JSON object", failures);
    return failures;
  }
  if (!isNonEmptyString(manifest.generated_at)) {
    fail("manifest.generated_at is required", failures);
  }
  if (!allowedTopStatuses.has(manifest.status)) {
    fail(`manifest.status must be one of: ${Array.from(allowedTopStatuses).join(", ")}`, failures);
  }
  if (!manifest.parallelization || typeof manifest.parallelization !== "object") {
    fail("manifest.parallelization is required", failures);
  } else {
    if (!Number.isInteger(manifest.parallelization.max_concurrent_lanes) || manifest.parallelization.max_concurrent_lanes < 1) {
      fail("manifest.parallelization.max_concurrent_lanes must be a positive integer", failures);
    }
    if (!isNonEmptyString(manifest.parallelization.final_lane)) {
      fail("manifest.parallelization.final_lane is required", failures);
    }
  }
  if (!Array.isArray(manifest.lanes) || manifest.lanes.length === 0) {
    fail("manifest.lanes must be a non-empty array", failures);
    return failures;
  }

  const ids = new Set();
  let nonComplete = 0;
  let sawFinalLane = false;

  for (const lane of manifest.lanes) {
    if (!lane || typeof lane !== "object" || Array.isArray(lane)) {
      fail("each lane must be an object", failures);
      continue;
    }
    if (!isNonEmptyString(lane.id)) {
      fail("each lane must have a non-empty id", failures);
      continue;
    }
    if (ids.has(lane.id)) {
      fail(`duplicate lane id: ${lane.id}`, failures);
    }
    ids.add(lane.id);
    if (lane.id === manifest.parallelization?.final_lane) {
      sawFinalLane = true;
    }
    if (!isNonEmptyString(lane.category)) {
      fail(`lane ${lane.id} must have a category`, failures);
    }
    if (!allowedLaneStatuses.has(lane.status)) {
      fail(`lane ${lane.id} has invalid status: ${lane.status}`, failures);
    }
    if (lane.status !== "complete") {
      nonComplete += 1;
    }
    if (typeof lane.can_parallelize !== "boolean") {
      fail(`lane ${lane.id} must declare can_parallelize as a boolean`, failures);
    }

    const writeScope = requireStringArray(lane, "write_scope", failures);
    const evidence = requireStringArray(lane, "evidence", failures);
    requireStringArray(lane, "local_commands", failures);
    const blockers = Array.isArray(lane.current_blockers) ? lane.current_blockers : [];
    const completionGate = requireStringArray(lane, "completion_gate", failures);

    if (lane.status === "complete" && blockers.length > 0) {
      fail(`lane ${lane.id} is complete but still lists blockers`, failures);
    }
    if (statusesRequiringExternalInput.has(lane.status)) {
      const externalInputs = Array.isArray(lane.external_inputs) ? lane.external_inputs.filter(isNonEmptyString) : [];
      if (externalInputs.length === 0) {
        fail(`lane ${lane.id} has status ${lane.status} but no external_inputs`, failures);
      }
      if (!evidence.includes(externalHandoffPath)) {
        fail(`lane ${lane.id} has status ${lane.status} but does not reference ${externalHandoffPath}`, failures);
      }
      if (!evidence.includes(externalRequirementsPath)) {
        fail(`lane ${lane.id} has status ${lane.status} but does not reference ${externalRequirementsPath}`, failures);
      }
    }
    if (lane.status !== "complete" && blockers.length === 0) {
      fail(`lane ${lane.id} is not complete but has no current_blockers`, failures);
    }

    for (const relativePath of evidence) {
      if (relativePath.includes("*") || relativePath.includes("<")) {
        continue;
      }
      const fullPath = path.join(repoRoot, relativePath);
      if (!fs.existsSync(fullPath) || fs.statSync(fullPath).size === 0) {
        fail(`lane ${lane.id} references missing or empty evidence: ${relativePath}`, failures);
      }
      const status = evidenceStatus(relativePath);
      if (lane.status === "complete" && status !== null && status !== "complete") {
        fail(`lane ${lane.id} is complete but ${relativePath} has Status: ${status}`, failures);
      }
    }

    for (const scopedPath of writeScope) {
      if (scopedPath.includes("..")) {
        fail(`lane ${lane.id} write_scope must not contain parent traversal: ${scopedPath}`, failures);
      }
    }
    if (completionGate.length < 1) {
      fail(`lane ${lane.id} must have at least one completion gate`, failures);
    }
  }

  if (!sawFinalLane) {
    fail(`final lane ${manifest.parallelization?.final_lane || "<missing>"} does not exist`, failures);
  }
  if (manifest.status === "ready" && nonComplete > 0) {
    fail(`manifest is ready but ${nonComplete} lanes are not complete`, failures);
  }
  if (manifest.status === "not_ready" && nonComplete === 0) {
    fail("manifest is not_ready but every lane is complete", failures);
  }

  return failures;
}

const manifest = readJson(manifestPath, []);
const failures = manifest ? validateManifest(manifest) : [`missing manifest: ${path.relative(repoRoot, manifestPath)}`];

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`FAIL: ${failure}`);
  }
  process.exit(1);
}

const nonComplete = manifest.lanes.filter((lane) => lane.status !== "complete").length;
console.log(`Commercial delivery lanes: OK (${manifest.lanes.length} lanes, status=${manifest.status}, non_complete=${nonComplete})`);
