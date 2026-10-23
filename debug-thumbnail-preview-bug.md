# Debug Session: thumbnail-preview-bug
- **Status**: [OPEN]
- **Issue**: Completed downloads in strict mode do not render the Ubuntu file explorer thumbnail in the app preview column even though the file already has a visible thumbnail in the system file explorer.
- **Debug Server**: http://127.0.0.1:7777/event
- **Log File**: .dbg/trae-debug-log-thumbnail-preview-bug.ndjson

## Reproduction Steps
1. Launch the app on Ubuntu.
2. Download a video until it reaches Completed.
3. Confirm the file shows a thumbnail in the Ubuntu file explorer.
4. Observe the app preview column for the same file.
5. Click the thumbnail area and verify whether an expanded preview opens.

## Hypotheses & Verification
| ID | Hypothesis | Likelihood | Effort | Evidence |
|----|------------|------------|--------|----------|
| A | The freedesktop thumbnail cache key/path calculation does not match Ubuntu's generated thumbnail entry for the downloaded file. | High | Low | Pending |
| B | Strict mode is still falling back to an empty/null pixmap because the preview request happens before the file manager thumbnail exists and is never retried once it does. | High | Medium | Pending |
| C | The preview QLabel receives a pixmap, but sizing or row/widget constraints keep it effectively invisible. | Medium | Low | Pending |
| D | Click handling for preview widgets is absent or attached to non-thumbnail states, so the expanded view requirement cannot be validated even when a pixmap exists. | High | Low | Pending |
| E | Completed/history refresh timing replaces thumbnail widgets after async resolution, dropping the loaded pixmap before the user sees it. | Medium | Medium | Pending |

## Log Evidence
- Pre-fix synthetic runtime reproduction shows the first preview request occurs before a cache thumbnail exists, then no automatic second strict lookup happens after the cache file appears.
- Current code also returns a non-strict Qt file icon when strict cache lookup fails, which masks the missing strict thumbnail state instead of retrying.
- Live Ubuntu evidence for `~/Videos/latest/1080-dcce...Full.mp4` shows no direct freedesktop cache hit exists, while GNOME's native thumbnail factory reports the file can be thumbnailed. This means strict mode needs the native GNOME thumbnailer path instead of cache-only lookup.

Pending.

## Verification Conclusion
| ID | Hypothesis | Status | Evidence Summary |
|----|------------|--------|------------------|
| A | The freedesktop cache lookup/pathing is wrong. | ✅ Confirmed | Post-fix synthetic cache-hit logs show strict lookup finds the Ubuntu-style cached PNG and assigns it successfully ([log lines 448-463 and 874](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L448-L463), [L874](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L874)). |
| B | A one-shot request misses thumbnails that appear later. | ✅ Confirmed | Delayed-cache test first logs a strict miss and null assignment ([lines 938-949](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L938-L949), [L1131](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L1131)), then a later retry hits and assigns the thumbnail ([lines 1470-1475](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L1470-L1475), [L1475](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L1475)). |
| C | Preview sizing/layout hides the image. | ❌ Rejected | Runtime logs and tests show label size is 128x128 and pixmap assignment succeeds when a strict thumbnail is present ([line 448](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L448), [L874](file:///home/treshen/Apps/gayzed-media/.dbg/trae-debug-log-thumbnail-preview-bug.ndjson#L874)). |
| D | Click-to-expand is missing. | ✅ Confirmed | There was no click-capable preview widget before the fix; post-fix offscreen runtime test reports `dialog_opened True`. |
| E | Table refresh timing drops thumbnail state. | ❌ Rejected | Preview requests consistently fire from history/queue refresh, so the primary failure is lookup/retry strategy rather than refresh suppression. |
