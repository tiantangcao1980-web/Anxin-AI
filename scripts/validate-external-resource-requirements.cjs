#!/usr/bin/env node
"use strict";

const fs = require("fs");

const DEFAULT_PATH = "docs/release/external-resource-requirements.json";
const PRIORITIES = new Set(["P0", "P1", "P2"]);
const STATUSES = new Set(["external_input_required", "in_progress", "complete"]);
const ITEM_TYPES = new Set([
  "account",
  "artifact",
  "config",
  "device_artifact",
  "env",
  "env_any_of",
  "env_boolean_true",
  "local_keychain",
  "mixed",
  "runner_arg",
]);
const FORBIDDEN_KEYS = new Set([
  "actual_value",
  "api_key",
  "password",
  "private_key",
  "secret_value",
  "session_key",
  "token",
  "value",
]);
const REQUIRED_DOCS = [
  "docs/release/external-inputs-checklist.md",
  "docs/release/external-resource-handoff.md",
  "docs/release/third-party-api-preparation.md",
  "docs/release/evidence-collection-runbook.md",
];
const REQUIRED_P0_TEMPLATE_ENVS = new Set([
  "PAYMENT_NOTIFY_BASE_URL",
  "WECHAT_PAY_APP_ID",
  "WECHAT_PAY_MCH_ID",
  "WECHAT_PAY_MERCHANT_SERIAL_NO",
  "WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH",
  "WECHAT_PAY_MERCHANT_PRIVATE_KEY",
  "WECHAT_PAY_PLATFORM_SERIAL",
  "WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH",
  "WECHAT_PAY_PLATFORM_PUBLIC_KEY",
  "WECHAT_PAY_API_V3_KEY",
  "WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED",
  "ALIPAY_APP_ID",
  "ALIPAY_PRIVATE_KEY_PATH",
  "ALIPAY_PRIVATE_KEY",
  "ALIPAY_PUBLIC_KEY_PATH",
  "ALIPAY_PUBLIC_KEY",
  "ALIPAY_GATEWAY_URL",
  "ALIPAY_OFFICIAL_WEBHOOK_ENABLED",
  "ESIGN_BAO_APP_ID",
  "ESIGN_BAO_APP_SECRET",
  "ESIGN_BAO_API_URL",
  "ESIGN_OFFICIAL_WEBHOOK_ENABLED",
  "FADADA_APP_ID",
  "FADADA_APP_SECRET",
  "FADADA_API_URL",
]);

function usage() {
  console.error("Usage: node scripts/validate-external-resource-requirements.cjs [manifest.json]");
}

function fail(message) {
  throw new Error(message);
}

function assertNonEmptyString(value, label) {
  if (typeof value !== "string" || value.trim() === "") {
    fail(`${label} must be a non-empty string`);
  }
}

function assertStringArray(value, label, minLength = 1) {
  if (!Array.isArray(value) || value.length < minLength) {
    fail(`${label} must be an array with at least ${minLength} item(s)`);
  }
  for (const item of value) {
    assertNonEmptyString(item, `${label}[]`);
  }
}

function walkNoSecretValues(value, path = "$") {
  if (!value || typeof value !== "object") {
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => walkNoSecretValues(item, `${path}[${index}]`));
    return;
  }
  for (const [key, child] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(key)) {
      fail(`${path}.${key} is forbidden; store only reference names, not real secrets`);
    }
    walkNoSecretValues(child, `${path}.${key}`);
  }
}

function checkEnvTemplates(envNames) {
  for (const template of [".env.example", "backend/.env.example"]) {
    const text = fs.readFileSync(template, "utf8");
    for (const envName of envNames) {
      const pattern = new RegExp(`^${envName}=`, "m");
      if (!pattern.test(text)) {
        fail(`${template} is missing required external env ${envName}`);
      }
    }
  }
}

function collectReferenceKeys(item) {
  return [
    "account_refs",
    "artifact_fields",
    "command_refs",
    "config_refs",
    "device_refs",
    "env_names",
    "runner_args",
  ].filter((key) => Array.isArray(item[key]) && item[key].length > 0);
}

function validateManifest(path) {
  const manifest = JSON.parse(fs.readFileSync(path, "utf8"));
  walkNoSecretValues(manifest);

  if (manifest.schema_version !== 1) {
    fail(`schema_version must be 1, got ${manifest.schema_version}`);
  }
  if (!STATUSES.has(manifest.status)) {
    fail(`invalid manifest status: ${manifest.status}`);
  }
  if (!manifest.storage_policy || typeof manifest.storage_policy !== "object") {
    fail("storage_policy is required");
  }
  assertStringArray(manifest.required_documents, "required_documents", REQUIRED_DOCS.length);

  for (const doc of REQUIRED_DOCS) {
    if (!manifest.required_documents.includes(doc)) {
      fail(`required_documents must include ${doc}`);
    }
    if (!fs.existsSync(doc)) {
      fail(`required document is missing: ${doc}`);
    }
  }

  if (!Array.isArray(manifest.resources) || manifest.resources.length < 1) {
    fail("resources must be a non-empty array");
  }

  const resourceIds = new Set();
  const manifestEnvNames = new Set();
  const templateRequiredEnvNames = new Set();
  let p0Count = 0;
  let itemCount = 0;

  for (const resource of manifest.resources) {
    assertNonEmptyString(resource.id, "resources[].id");
    if (resourceIds.has(resource.id)) {
      fail(`duplicate resource id: ${resource.id}`);
    }
    resourceIds.add(resource.id);

    if (!PRIORITIES.has(resource.priority)) {
      fail(`${resource.id} has invalid priority: ${resource.priority}`);
    }
    if (resource.priority === "P0") {
      p0Count += 1;
    }
    if (!STATUSES.has(resource.status)) {
      fail(`${resource.id} has invalid status: ${resource.status}`);
    }
    assertNonEmptyString(resource.lane, `${resource.id}.lane`);
    assertNonEmptyString(resource.title, `${resource.id}.title`);
    assertStringArray(resource.commands_after_receipt, `${resource.id}.commands_after_receipt`);
    assertStringArray(resource.completion_evidence, `${resource.id}.completion_evidence`);

    if (!Array.isArray(resource.items) || resource.items.length < 1) {
      fail(`${resource.id}.items must be a non-empty array`);
    }
    const itemIds = new Set();
    for (const item of resource.items) {
      itemCount += 1;
      assertNonEmptyString(item.id, `${resource.id}.items[].id`);
      if (itemIds.has(item.id)) {
        fail(`${resource.id} has duplicate item id: ${item.id}`);
      }
      itemIds.add(item.id);

      assertNonEmptyString(item.label, `${resource.id}.${item.id}.label`);
      if (!ITEM_TYPES.has(item.type)) {
        fail(`${resource.id}.${item.id} has invalid type: ${item.type}`);
      }
      if (typeof item.secret !== "boolean") {
        fail(`${resource.id}.${item.id}.secret must be boolean`);
      }
      assertStringArray(item.required_for, `${resource.id}.${item.id}.required_for`);

      const referenceKeys = collectReferenceKeys(item);
      if (referenceKeys.length === 0) {
        fail(`${resource.id}.${item.id} must include at least one reference array`);
      }

      if (Array.isArray(item.env_names)) {
        assertStringArray(item.env_names, `${resource.id}.${item.id}.env_names`);
        for (const envName of item.env_names) {
          manifestEnvNames.add(envName);
          if (item.template_required === true) {
            templateRequiredEnvNames.add(envName);
          }
        }
      }
      if (item.type.startsWith("env") && !Array.isArray(item.env_names)) {
        fail(`${resource.id}.${item.id} is ${item.type} but has no env_names`);
      }
    }
  }

  if (p0Count < 6) {
    fail(`expected at least 6 P0 external resource groups, got ${p0Count}`);
  }

  for (const envName of REQUIRED_P0_TEMPLATE_ENVS) {
    if (!manifestEnvNames.has(envName)) {
      fail(`manifest is missing required P0 env ${envName}`);
    }
    if (!templateRequiredEnvNames.has(envName)) {
      fail(`manifest must mark ${envName} with template_required=true`);
    }
  }

  checkEnvTemplates(templateRequiredEnvNames);

  return {
    path,
    resources: manifest.resources.length,
    p0Count,
    itemCount,
    envCount: manifestEnvNames.size,
  };
}

function main() {
  const args = process.argv.slice(2);
  if (args.length > 1 || args.includes("-h") || args.includes("--help")) {
    usage();
    return args.length > 1 ? 2 : 0;
  }

  try {
    const result = validateManifest(args[0] || DEFAULT_PATH);
    console.log(
      `External resource requirements: OK (${result.resources} resources, p0=${result.p0Count}, items=${result.itemCount}, envs=${result.envCount})`
    );
    return 0;
  } catch (error) {
    console.error(`External resource requirements: FAIL - ${error.message}`);
    return 1;
  }
}

if (require.main === module) {
  process.exitCode = main();
}
