#!/usr/bin/env bash
# Redacted desktop release preflight for signed/notarized packaged evidence.
#
# This checks the local release packaging prerequisites without performing
# signing, notarization, stapling, or network calls. It is supporting evidence
# only; keep docs/release/evidence/desktop-runtime-smoke.md pending until a
# signed/notarized package has real runtime/profile/cross-device evidence.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/desktop-release-preflight.sh [--out path]

Environment overrides:
  ANXIN_DESKTOP_RELEASE_APP              Release .app path to inspect.
  ANXIN_DESKTOP_DEBUG_APP                Debug .app path used as supporting evidence.
  ANXIN_DESKTOP_INSTALLED_PROFILE_REPORT Installed-profile SQLCipher/keyring JSON report.
  ANXIN_DESKTOP_RUNTIME_TRANSCRIPT       Runtime smoke transcript path.
  ANXIN_DESKTOP_RUNTIME_ARTIFACT         Structured runtime smoke JSON artifact.
  NOTARYTOOL_KEYCHAIN_PROFILE            Preferred notarytool credential profile.
  APPLE_ID / APPLE_TEAM_ID / APPLE_APP_SPECIFIC_PASSWORD
  APP_STORE_CONNECT_API_KEY_ID / APP_STORE_CONNECT_API_ISSUER_ID / APP_STORE_CONNECT_API_KEY_PATH

This command writes a redacted JSON artifact and exits 0 even when release
prerequisites are missing. The artifact's release_ready field is the gate signal.
EOF
}

OUT_PATH=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --out)
      OUT_PATH="${2:-}"
      if [ -z "$OUT_PATH" ]; then
        usage
        echo "ERROR: --out requires a path" >&2
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

node - "$OUT_PATH" <<'NODE'
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const projectRoot = process.cwd();
const outPath = process.argv[2] || "";
const releaseApp = process.env.ANXIN_DESKTOP_RELEASE_APP ||
  "desktop/target/release/bundle/macos/安心法务.app";
const debugApp = process.env.ANXIN_DESKTOP_DEBUG_APP ||
  "desktop/target/debug/bundle/macos/安心法务.app";
const installedProfileReport = process.env.ANXIN_DESKTOP_INSTALLED_PROFILE_REPORT ||
  latestArtifact(/^desktop-installed-profile(?:-smoke)?-\d{8}\.json$/) ||
  "/tmp/anxin-desktop-installed-profile-smoke.json";
const runtimeTranscript = process.env.ANXIN_DESKTOP_RUNTIME_TRANSCRIPT ||
  latestArtifact(/^desktop-runtime-ui-smoke-\d{8}\.log$/) ||
  "/tmp/anxin-desktop-runtime-smoke-with-ui-20260507.log";
const runtimeStructuredArtifact = process.env.ANXIN_DESKTOP_RUNTIME_ARTIFACT ||
  latestArtifact(/^desktop-runtime-code-smoke-\d{8}\.json$/) ||
  "";

function resolvePath(value) {
  return path.isAbsolute(value) ? value : path.join(projectRoot, value);
}

function exists(value) {
  if (!value) return false;
  return fs.existsSync(resolvePath(value));
}

function readJson(value) {
  if (!value) return null;
  try {
    return JSON.parse(fs.readFileSync(resolvePath(value), "utf8"));
  } catch {
    return null;
  }
}

function readText(value) {
  if (!value) return "";
  try {
    return fs.readFileSync(resolvePath(value), "utf8");
  } catch {
    return "";
  }
}

function latestArtifact(pattern) {
  const artifactDir = path.join(projectRoot, "docs", "release", "evidence", "artifacts");
  try {
    return fs
      .readdirSync(artifactDir)
      .filter((name) => pattern.test(name))
      .map((name) => {
        const relativePath = path.join("docs", "release", "evidence", "artifacts", name);
        const absolutePath = path.join(projectRoot, relativePath);
        return {
          relativePath,
          modifiedAt: fs.statSync(absolutePath).mtimeMs,
        };
      })
      .sort((a, b) => b.modifiedAt - a.modifiedAt || b.relativePath.localeCompare(a.relativePath))[0]
      ?.relativePath || null;
  } catch {
    return null;
  }
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  return {
    command: [command, ...args].join(" "),
    status: result.status,
    stdout: result.stdout || "",
    stderr: result.stderr || "",
    ok: result.status === 0,
  };
}

function commandExists(command) {
  return run("bash", ["-lc", `command -v ${JSON.stringify(command)} >/dev/null`]).ok;
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

const checks = [];
function addCheck(id, label, status, releaseBlocking, detail = {}) {
  checks.push({ id, label, status, release_blocking: releaseBlocking, detail });
}

const now = new Date().toISOString();
const isMac = process.platform === "darwin";
addCheck(
  "platform",
  "macOS release packaging host",
  isMac ? "pass" : "fail",
  true,
  { platform: process.platform, required: "darwin" },
);

for (const command of ["xcodebuild", "xcrun", "codesign", "security", "spctl", "hdiutil"]) {
  addCheck(
    `command.${command}`,
    `${command} available`,
    commandExists(command) ? "pass" : "fail",
    true,
  );
}

if (isMac && commandExists("hdiutil")) {
  const hdiutilProbe = probeHdiutilCreate();
  addCheck(
    "dmg.hdiutil_create_probe",
    "hdiutil can create a temporary DMG",
    hdiutilProbe.ok ? "pass" : "fail",
    true,
    hdiutilProbe,
  );
} else {
  addCheck(
    "dmg.hdiutil_create_probe",
    "hdiutil can create a temporary DMG",
    "fail",
    true,
    { skipped: true, reason: isMac ? "hdiutil command missing" : "not macOS" },
  );
}

const tauriConfig = readJson("desktop/tauri.conf.json");
const signingIdentity = tauriConfig?.bundle?.macOS?.signingIdentity ?? null;
addCheck(
  "tauri.signing_identity",
  "Tauri macOS signing identity configured",
  typeof signingIdentity === "string" && signingIdentity.trim() ? "pass" : "fail",
  true,
  {
    configured: typeof signingIdentity === "string" && signingIdentity.trim().length > 0,
    value_redacted: signingIdentity ? "<configured>" : null,
  },
);

const entitlementsPath = tauriConfig?.bundle?.macOS?.entitlements || "Entitlements.plist";
const entitlementsRelativePath = path.join("desktop", entitlementsPath);
const entitlementsText = readText(entitlementsRelativePath);
const apsEnvironmentMatch = entitlementsText.match(
  /<key>\s*com\.apple\.developer\.aps-environment\s*<\/key>\s*<string>\s*([^<]+)\s*<\/string>/,
);
addCheck(
  "tauri.entitlements",
  "macOS entitlements file exists",
  exists(entitlementsRelativePath) ? "pass" : "fail",
  true,
  { path: entitlementsRelativePath },
);
addCheck(
  "tauri.entitlements.aps_environment",
  "macOS APNs entitlement uses production for release",
  apsEnvironmentMatch ? (apsEnvironmentMatch[1] === "production" ? "pass" : "fail") : "warn",
  Boolean(apsEnvironmentMatch),
  {
    path: entitlementsRelativePath,
    aps_environment: apsEnvironmentMatch?.[1] || null,
    required_for_release: apsEnvironmentMatch ? "production" : null,
  },
);

if (commandExists("security")) {
  const identity = run("security", ["find-identity", "-v", "-p", "codesigning"]);
  const validMatch = identity.stdout.match(/(\d+)\s+valid identities found/);
  const validIdentityCount = validMatch ? Number(validMatch[1]) : 0;
  addCheck(
    "codesign.identities",
    "Apple code signing identities installed",
    validIdentityCount > 0 ? "pass" : "fail",
    true,
    { valid_identity_count: validIdentityCount },
  );
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
addCheck(
  "notary.credentials",
  "Notarization credentials configured",
  keychainProfileConfigured || appleIdConfigured || appStoreConnectConfigured ? "pass" : "fail",
  true,
  {
    keychain_profile_configured: keychainProfileConfigured,
    apple_id_flow_configured: appleIdConfigured,
    app_store_connect_api_configured: appStoreConnectConfigured,
  },
);

if (commandExists("xcrun")) {
  addCheck(
    "notary.tool",
    "notarytool available",
    run("xcrun", ["--find", "notarytool"]).ok ? "pass" : "fail",
    true,
  );
  addCheck(
    "stapler.tool",
    "stapler available",
    run("xcrun", ["--find", "stapler"]).ok ? "pass" : "fail",
    true,
  );
}

const releaseAppExists = exists(releaseApp);
addCheck(
  "release.app.exists",
  "Release .app path exists",
  releaseAppExists ? "pass" : "fail",
  true,
  { path: releaseApp },
);

if (releaseAppExists && commandExists("codesign")) {
  const verify = run("codesign", ["--verify", "--deep", "--strict", "--verbose=2", resolvePath(releaseApp)]);
  addCheck(
    "release.app.codesign_verify",
    "Release .app code signature verifies",
    verify.ok ? "pass" : "fail",
    true,
    { exit_code: verify.status },
  );
  const display = run("codesign", ["--display", "--verbose=4", resolvePath(releaseApp)]);
  const authorities = display.stderr
    .split(/\r?\n/)
    .filter((line) => line.startsWith("Authority=")).length;
  addCheck(
    "release.app.signature_authority",
    "Release .app has signing authority chain",
    authorities > 0 ? "pass" : "fail",
    true,
    { authority_count: authorities },
  );
}

if (releaseAppExists && commandExists("spctl")) {
  const assess = run("spctl", ["--assess", "--type", "execute", "--verbose=2", resolvePath(releaseApp)]);
  addCheck(
    "release.app.gatekeeper_assess",
    "Release .app passes Gatekeeper assessment",
    assess.ok ? "pass" : "fail",
    true,
    { exit_code: assess.status },
  );
}

const dmgDir = "desktop/target/release/bundle/dmg";
const releaseDmgExists = exists(dmgDir) && fs.readdirSync(resolvePath(dmgDir)).some((name) => name.endsWith(".dmg"));
addCheck(
  "release.dmg.exists",
  "Release DMG path exists",
  releaseDmgExists ? "pass" : "fail",
  true,
  { path: dmgDir },
);

addCheck(
  "support.debug_app.exists",
  "Debug .app supporting evidence exists",
  exists(debugApp) ? "pass" : "warn",
  false,
  { path: debugApp },
);

const runtimeLog = readText(runtimeTranscript);
const runtimeArtifact = readJson(runtimeStructuredArtifact);
const hasStructuredRuntimePageLoad = Boolean(
  runtimeArtifact?.mode === "desktop_runtime_code_smoke" &&
    runtimeArtifact?.status === "passed" &&
    runtimeArtifact?.checks?.debug_app_bundle_ui_load === "passed",
);
const hasRuntimePageLoad =
  (runtimeLog.includes("desktop runtime UI smoke response:") &&
    runtimeLog.includes('"pageLoadFinished":true') &&
    runtimeLog.includes('"webviewLabel":"main"')) ||
  hasStructuredRuntimePageLoad;
addCheck(
  "support.debug_runtime_transcript",
  "Debug .app runtime/WebView transcript exists",
  hasRuntimePageLoad ? "pass" : "warn",
  false,
  {
    path: runtimeTranscript,
    structured_artifact: runtimeStructuredArtifact || null,
    page_load_evidence: hasRuntimePageLoad,
    structured_artifact_evidence: hasStructuredRuntimePageLoad,
  },
);

const installedReport = readJson(installedProfileReport);
const installedProfilePass = Boolean(
  installedReport?.firstLaunch?.keyringRoundTrip &&
    installedReport?.firstLaunch?.encryptedReopen &&
    installedReport?.firstLaunch?.plaintextOpenBlocked &&
    installedReport?.secondLaunch?.keyringRoundTrip &&
    installedReport?.secondLaunch?.encryptedReopen &&
    installedReport?.secondLaunch?.plaintextOpenBlocked,
);
addCheck(
  "support.installed_profile_report",
  "Installed-profile SQLCipher/keyring report exists",
  installedProfilePass ? "pass" : "warn",
  false,
  { path: installedProfileReport, supporting_evidence_complete: installedProfilePass },
);

const blockingFailures = checks
  .filter((check) => check.release_blocking && check.status !== "pass")
  .map((check) => check.id);

const report = {
  generated_at: now,
  mode: "preflight",
  release_ready: blockingFailures.length === 0,
  release_blockers: blockingFailures,
  inputs: {
    release_app: releaseApp,
    debug_app: debugApp,
    installed_profile_report: installedProfileReport,
    runtime_transcript: runtimeTranscript,
    runtime_structured_artifact: runtimeStructuredArtifact || null,
  },
  checks,
  completion_note:
    "Supporting evidence only. Keep desktop runtime evidence pending until a signed/notarized package has packaged UI interaction, signed packaged-profile migration, signed packaged runtime performance, and cross-device continuation evidence.",
};

const text = JSON.stringify(report, null, 2);
if (outPath) {
  const absoluteOut = resolvePath(outPath);
  fs.mkdirSync(path.dirname(absoluteOut), { recursive: true });
  fs.writeFileSync(absoluteOut, `${text}\n`);
  console.log(`Wrote redacted desktop release preflight artifact: ${absoluteOut}`);
} else {
  console.log(text);
}

console.log("Desktop release preflight summary:");
for (const check of checks) {
  const marker = check.status === "pass" ? "pass" : check.release_blocking ? "missing" : "supporting";
  console.log(`  - ${check.id}: ${marker}`);
}
if (blockingFailures.length) {
  console.log("  release_ready: false");
  for (const blocker of blockingFailures) {
    console.log(`    blocker: ${blocker}`);
  }
} else {
  console.log("  release_ready: true");
}
NODE
