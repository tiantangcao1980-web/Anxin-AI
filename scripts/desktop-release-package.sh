#!/usr/bin/env bash
# Build and verify the signed/notarized desktop release package when Apple
# signing resources are available.
#
# Default mode is dry-run so local development can produce redacted evidence
# without creating signed artifacts or making notarization network calls.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/desktop-release-package.sh [options]

Options:
  --dry-run              Inspect inputs and write a package readiness artifact without building.
  --out path             Write a redacted package JSON artifact.
  --preflight-out path   Write desktop-release-preflight output after build or dry-run.
  --skip-build           Do not run cargo tauri build; useful after an external CI build.
  --skip-stapling        Pass --skip-stapling to cargo tauri build.
  -h, --help             Show this help.

Environment:
  ANXIN_DESKTOP_SIGNING_IDENTITY or APPLE_SIGNING_IDENTITY
  ANXIN_DESKTOP_RELEASE_BUNDLES  Default: app,dmg
  ANXIN_DESKTOP_TARGET           Optional cargo target triple.
  NOTARYTOOL_KEYCHAIN_PROFILE or Apple ID / App Store Connect notarization env

This script never writes secrets to artifacts. It writes only redacted booleans,
commands, release blockers, and paths.
EOF
}

DRY_RUN=0
SKIP_BUILD=0
SKIP_STAPLING=0
OUT_PATH=""
PREFLIGHT_OUT_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-build)
      SKIP_BUILD=1
      shift
      ;;
    --skip-stapling)
      SKIP_STAPLING=1
      shift
      ;;
    --out)
      OUT_PATH="${2:-}"
      if [ -z "$OUT_PATH" ]; then
        usage
        echo "ERROR: --out requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    --preflight-out)
      PREFLIGHT_OUT_PATH="${2:-}"
      if [ -z "$PREFLIGHT_OUT_PATH" ]; then
        usage
        echo "ERROR: --preflight-out requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

node - "$OUT_PATH" "$PREFLIGHT_OUT_PATH" "$DRY_RUN" "$SKIP_BUILD" "$SKIP_STAPLING" <<'NODE'
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const projectRoot = process.cwd();
const outPath = process.argv[2] || "";
const preflightOutPath = process.argv[3] || "";
const dryRun = process.argv[4] === "1";
const skipBuild = process.argv[5] === "1";
const skipStapling = process.argv[6] === "1";
const signingIdentity = process.env.ANXIN_DESKTOP_SIGNING_IDENTITY || process.env.APPLE_SIGNING_IDENTITY || "";
const bundles = process.env.ANXIN_DESKTOP_RELEASE_BUNDLES || "app,dmg";
const target = process.env.ANXIN_DESKTOP_TARGET || "";

function resolvePath(value) {
  if (!value) return "";
  return path.isAbsolute(value) ? value : path.join(projectRoot, value);
}

function commandExists(command) {
  return spawnSync("bash", ["-lc", `command -v ${JSON.stringify(command)} >/dev/null`], {
    cwd: projectRoot,
    encoding: "utf8",
  }).status === 0;
}

function tailLines(text, maxLines = 6) {
  return String(text || "").split(/\r?\n/).filter(Boolean).slice(-maxLines);
}

function probeHdiutilCreate() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "anxin-hdiutil-probe."));
  const probeDmg = path.join(tempDir, "probe.dmg");
  try {
    const result = spawnSync(
      "hdiutil",
      ["create", "-size", "8m", "-fs", "HFS+", "-volname", "AnxinProbe", "-ov", probeDmg],
      {
        cwd: projectRoot,
        encoding: "utf8",
        maxBuffer: 2 * 1024 * 1024,
      },
    );
    return {
      ok: result.status === 0,
      exit_code: result.status,
      stdout_tail: tailLines(result.stdout),
      stderr_tail: tailLines(result.stderr),
    };
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd || projectRoot,
    env: options.env || process.env,
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024,
  });
  return {
    command: [command, ...args].join(" "),
    exit_code: result.status,
    status: result.status === 0 ? "pass" : "fail",
    stdout_tail: (result.stdout || "").split(/\r?\n/).filter(Boolean).slice(-20),
    stderr_tail: (result.stderr || "").split(/\r?\n/).filter(Boolean).slice(-20),
  };
}

function writeJson(value, targetPath) {
  if (!targetPath) return;
  const absolute = resolvePath(targetPath);
  fs.mkdirSync(path.dirname(absolute), { recursive: true });
  fs.writeFileSync(absolute, JSON.stringify(value, null, 2) + "\n", "utf8");
}

function readJson(targetPath) {
  try {
    return JSON.parse(fs.readFileSync(resolvePath(targetPath), "utf8"));
  } catch {
    return null;
  }
}

const checks = [];
const commands = [];
function addCheck(id, label, passed, releaseBlocking, detail = {}) {
  checks.push({
    id,
    label,
    status: passed ? "pass" : "fail",
    release_blocking: releaseBlocking,
    detail,
  });
}

const keychainProfileConfigured = Boolean(process.env.NOTARYTOOL_KEYCHAIN_PROFILE);
const appleIdConfigured = Boolean(
  process.env.APPLE_ID &&
    process.env.APPLE_TEAM_ID &&
    process.env.APPLE_APP_SPECIFIC_PASSWORD,
);
const appStoreConnectConfigured = Boolean(
  process.env.APP_STORE_CONNECT_API_KEY_ID &&
    process.env.APP_STORE_CONNECT_API_ISSUER_ID &&
    process.env.APP_STORE_CONNECT_API_KEY_PATH,
);

const entitlementsPath = path.join(projectRoot, "desktop", "Entitlements.plist");
const entitlementsText = fs.existsSync(entitlementsPath) ? fs.readFileSync(entitlementsPath, "utf8") : "";
const apsEnvironment = entitlementsText.match(
  /<key>\s*com\.apple\.developer\.aps-environment\s*<\/key>\s*<string>\s*([^<]+)\s*<\/string>/,
)?.[1] || "";

addCheck("platform", "macOS release packaging host", process.platform === "darwin", true, { platform: process.platform });
addCheck("command.cargo", "cargo available", commandExists("cargo"), true);
addCheck("command.xcrun", "xcrun available", commandExists("xcrun"), true);
addCheck("command.codesign", "codesign available", commandExists("codesign"), true);
addCheck("command.hdiutil", "hdiutil available", commandExists("hdiutil"), bundles.includes("dmg"));
if (bundles.includes("dmg") && process.platform === "darwin" && commandExists("hdiutil")) {
  const hdiutilProbe = probeHdiutilCreate();
  addCheck(
    "dmg.hdiutil_create_probe",
    "hdiutil can create a temporary DMG",
    hdiutilProbe.ok,
    true,
    hdiutilProbe,
  );
} else {
  addCheck(
    "dmg.hdiutil_create_probe",
    "hdiutil can create a temporary DMG",
    !bundles.includes("dmg"),
    bundles.includes("dmg"),
    {
      skipped: true,
      reason: bundles.includes("dmg")
        ? process.platform === "darwin"
          ? "hdiutil command missing"
          : "not macOS"
        : "DMG bundle not requested",
    },
  );
}
addCheck("signing.identity", "Developer ID signing identity provided", Boolean(signingIdentity.trim()), true, {
  configured: Boolean(signingIdentity.trim()),
});
addCheck(
  "notary.credentials",
  "Notarization credentials configured",
  keychainProfileConfigured || appleIdConfigured || appStoreConnectConfigured,
  true,
  {
    keychain_profile_configured: keychainProfileConfigured,
    apple_id_flow_configured: appleIdConfigured,
    app_store_connect_api_configured: appStoreConnectConfigured,
  },
);
addCheck("entitlements.aps_environment", "APNs entitlement is production", apsEnvironment === "production", Boolean(apsEnvironment), {
  aps_environment: apsEnvironment || null,
  required_for_release: apsEnvironment ? "production" : null,
});

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "anxin-desktop-release-config."));
const configPath = path.join(tempDir, "tauri.release.conf.json");
fs.writeFileSync(
  configPath,
  JSON.stringify({ bundle: { macOS: { signingIdentity: signingIdentity || null } } }, null, 2) + "\n",
  "utf8",
);

const preBuildBlockers = checks
  .filter((check) => check.release_blocking && check.status !== "pass")
  .map((check) => check.id);

let status = preBuildBlockers.length ? "blocked" : "ready";
if (!dryRun && !preBuildBlockers.length && !skipBuild) {
  const args = ["tauri", "build", "--ci", "--bundles", bundles, "--config", configPath];
  if (target) args.push("--target", target);
  if (skipStapling) args.push("--skip-stapling");
  const buildResult = run("cargo", args, { cwd: path.join(projectRoot, "desktop") });
  commands.push(buildResult);
  status = buildResult.status === "pass" ? "built" : "failed";
}

let preflight = null;
if (preflightOutPath) {
  const preflightResult = run("bash", [
    "scripts/desktop-release-preflight.sh",
    "--out",
    preflightOutPath,
  ]);
  commands.push(preflightResult);
  preflight = readJson(preflightOutPath);
  if (preflight?.release_ready === true && (status === "built" || (skipBuild && status === "ready"))) {
    status = "packaged_preflight_passed";
  }
}

const releaseBlockers = [
  ...new Set([
    ...preBuildBlockers,
    ...(preflight?.release_blockers || []),
    ...(status === "failed" ? ["cargo.tauri.build"] : []),
  ]),
];

const report = {
  generated_at: new Date().toISOString(),
  mode: "desktop_release_package",
  status: dryRun ? "dry_run" : status,
  release_evidence_complete: false,
  release_ready: releaseBlockers.length === 0 && !dryRun && status === "packaged_preflight_passed",
  release_blockers: releaseBlockers,
  inputs: {
    dry_run: dryRun,
    skip_build: skipBuild,
    skip_stapling: skipStapling,
    bundles,
    target: target || null,
    signing_identity_configured: Boolean(signingIdentity.trim()),
  },
  checks,
  commands,
  preflight_artifact: preflightOutPath || null,
  completion_note:
    "Supporting evidence only. Keep desktop runtime evidence pending until signed/notarized package smoke, signed packaged-profile migration, signed packaged runtime performance, and cross-device continuation artifacts are attached.",
};

writeJson(report, outPath);
if (outPath) {
  console.log(`Wrote redacted desktop release package artifact: ${resolvePath(outPath)}`);
} else {
  console.log(JSON.stringify(report, null, 2));
}
if (releaseBlockers.length) {
  console.log("Desktop release package is blocked:");
  for (const blocker of releaseBlockers) console.log(`  - ${blocker}`);
} else {
  console.log("Desktop release package preflight is ready.");
}
NODE
