#!/usr/bin/env bash
# Guard code-level desktop MVP surfaces that are still waiting on signed/runtime evidence.
#
# This is intentionally structural: full compile/test/browser coverage remains in
# commercial-readiness-gate.sh --with-local-tests, while this gate makes quick
# release checks fail if the local desktop workstation, quick-query, or file-drop
# chains drift out of the expected code and documentation shape.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 - <<'PY'
from pathlib import Path

root = Path(".")
failures: list[str] = []


def require_fragments(relative: str, fragments: list[str]) -> None:
    path = root / relative
    if not path.exists():
        failures.append(f"{relative}: missing")
        return
    text = path.read_text(encoding="utf-8")
    for fragment in fragments:
        if fragment not in text:
            failures.append(f"{relative}: missing fragment {fragment!r}")


checks = {
    "desktop/src/commands/quick_query.rs": [
        "QUICK_QUERY_WINDOW_LABEL",
        "QUICK_QUERY_WINDOW_PATH",
        "/desktop/quick-query",
        "hide_quick_query_window",
        "always_on_top: true",
        "skip_taskbar: true",
    ],
    "desktop/src/commands/local_llm.rs": [
        "get_local_llm_config",
        "set_default_local_model",
        "normalize_local_model_name",
        "configured_default_model",
    ],
    "desktop/src/commands/native_notification.rs": [
        "DesktopNotificationKind",
        "build_desktop_notification_preview",
        "send_desktop_notification",
        "get_desktop_notification_permission",
        "request_desktop_notification_permission",
        "DesktopNotificationPermissionResponse",
        "local_only",
        "safe_in_top_secret",
    ],
    "desktop/src/commands/offline_tasks.rs": [
        "list_offline_tasks",
        "retry_failed_offline_tasks",
        "process_local_offline_tasks",
        "OfflineQueueRetryReport",
        "OfflineQueueProcessReport",
        "desktop_builtin_text_summary_v1",
        "local_result_preview",
        "本地路径仅保存在加密队列",
    ],
    "desktop/src/services/offline_queue.rs": [
        "recent_tasks_sql",
        "retry_failed_sql",
        "queued_local_tasks_sql",
        "flushable",
    ],
    "desktop/src/services/runtime_config.rs": [
        "local_model",
        "normalize_local_model_name",
        "DEFAULT_LOCAL_MODEL",
        "skip_serializing_if",
    ],
    "desktop/src/lib.rs": [
        "Cmd+Shift+Space",
        "Cmd/Ctrl+Shift+Space",
        "toggle_quick_query_window",
        "hide_quick_query_window",
        "set_default_local_model",
        "send_desktop_notification",
        "get_desktop_notification_permission",
        "request_desktop_notification_permission",
        "list_offline_tasks",
        "retry_failed_offline_tasks",
        "process_local_offline_tasks",
        "queue_file_drop_paths",
    ],
    "frontend/src/pages/QuickQuery.tsx": [
        "hideQuickQueryWindow",
        "localLLMChat",
        "mode: 'quick_query'",
        "Escape",
        "blur",
    ],
    "frontend/src/pages/quickQueryModel.ts": [
        "QUICK_QUERY_AUTO_HIDE_MS",
        "shouldUseLocalQuickQuery",
        "resolveLocalQuickQueryAnswer",
    ],
    "frontend/src/pages/quickQueryModel.test.ts": [
        "shouldUseLocalQuickQuery",
        "resolveLocalQuickQueryAnswer",
    ],
    "frontend/e2e/quick-query.spec.ts": [
        "/desktop/quick-query",
        "hide_quick_query_window",
    ],
    "desktop/src/commands/file_drop.rs": [
        "queue_file_drop_paths",
        "desktop://file-queued",
        "contract_review",
        "document_summary",
        "local_path",
    ],
    "frontend/src/lib/tauri-bridge.ts": [
        "getLocalLLMConfig",
        "setDefaultLocalModel",
        "DesktopNotificationKind",
        "previewDesktopNotification",
        "getDesktopNotificationPermission",
        "requestDesktopNotificationPermission",
        "sendDesktopNotification",
        "queueFileDropPaths",
        "listenFileDropQueued",
        "listenDesktopFileDrops",
        "listOfflineTasks",
        "retryFailedOfflineTasks",
        "processLocalOfflineTasks",
        "localResultPreview",
        "desktop://file-queued",
    ],
    "frontend/src/lib/desktopFileDropEvents.ts": [
        "summarizeFileDropQueueReport",
        "extractDesktopFileDropPaths",
        "部分文件已加入队列",
    ],
    "frontend/src/lib/desktopFileDropEvents.test.ts": [
        "summarizeFileDropQueueReport",
        "extractDesktopFileDropPaths",
    ],
    "frontend/src/App.tsx": [
        "listenFileDropQueued",
        "listenDesktopFileDrops",
        "queueFileDropPaths",
        "/desktop/quick-query",
    ],
    "frontend/src/components/desktop/DesktopWorkstationPanel.tsx": [
        "DesktopWorkstationPanel",
        "本地模型管理",
        "local-model-save",
        "本机通知",
        "native-notification-permission-action",
        "native-notification-test",
        "desktop-offline-queue-manager",
        "offline-queue-retry-failed",
        "offline-queue-process-local",
        "本机结果",
        "本机运行配置",
        "后端环境",
    ],
    "frontend/src/components/desktop/desktopWorkstationModel.ts": [
        "buildDesktopNotificationReadiness",
        "native-notification",
        "extractLocalModelOptions",
        "normalizeLocalModelInput",
        "normalizeWorkstationBackendUrl",
        "top-secret",
        "hybrid",
        "cloud",
    ],
    "frontend/src/components/desktop/desktopWorkstationModel.test.ts": [
        "buildDesktopNotificationReadiness",
        "native notification local-only",
        "extractLocalModelOptions",
        "normalizeLocalModelInput",
        "normalizeWorkstationBackendUrl",
        "top-secret",
    ],
    "frontend/e2e/settings-workstation.spec.ts": [
        "settings?tab=workstation",
        "settings?tab=privacy",
        "request_desktop_notification_permission",
        "retry_failed_offline_tasks",
        "process_local_offline_tasks",
        "send_desktop_notification",
        "offline-queue-retry-failed",
        "offline-queue-process-local",
        "native-notification-permission-action",
        "native-notification-test",
        "local-model-save",
        "desktop runtime",
    ],
    "docs/desktop/quick-query-flow.md": [
        "Cmd/Ctrl+Shift+Space",
        "/desktop/quick-query",
        "hide_quick_query_window",
        "Still Pending",
    ],
    "docs/release/test-evidence.md": [
        "桌面快问 P0-2",
        "桌面本地模型管理",
        "桌面本机通知",
        "桌面文件拖入分析 P0-3",
        "桌面主窗口 WebView 文件 drop",
    ],
    "docs/release/commercial-delivery-readiness.md": [
        "桌面端补充：`Cmd/Ctrl+Shift+Space`",
        "桌面本地模型默认配置",
        "桌面本机通知",
        "桌面端补充：文件拖入分析",
    ],
    "docs/audit/11a-desktop-mvp/00-prd-reality-gap.md": [
        "Desktop MVP",
        "P0-1",
        "P0-8",
        "signed packaged runtime",
    ],
    "docs/audit/11a-desktop-mvp/01-prd-coverage.md": [
        "PRD Coverage",
        "P0-1 desktop window chrome",
        "P0-8 workstation configuration write surface",
    ],
    "docs/audit/11a-desktop-mvp/02-issues.md": [
        "DSK-001",
        "DSK-009",
        "Release Interpretation",
    ],
    "docs/audit/11a-desktop-mvp/03-fixes.md": [
        "Quick Query",
        "File Drop Analysis Queue",
        "default local model persistence",
        "native notification bridge",
        "Remote-Control Host",
    ],
    "docs/audit/11a-desktop-mvp/04-test-additions.md": [
        "desktop-mvp-local-gate.sh",
        "quickQueryModel.test.ts",
        "native notification local-only",
        "Not Covered Locally",
    ],
    "docs/audit/11a-desktop-mvp/05-followups.md": [
        "Remaining P0",
        "Evidence Owners",
        "Release Risk",
    ],
}

for relative, fragments in checks.items():
    require_fragments(relative, fragments)

if failures:
    for failure in failures:
        print(f"Desktop MVP local gate: FAIL: {failure}")
    raise SystemExit(1)

print("Desktop MVP local gate: PASS")
PY
