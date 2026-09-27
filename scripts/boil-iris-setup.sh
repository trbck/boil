#!/bin/sh
# boil-iris-setup — give every coding agent on this host a camera.
#
# iris (https://github.com/brijr/iris) turns one command or one MCP `capture` call into one
# screenshot: a page, a viewport preset, or a single element by CSS selector. Its exit code is
# the verdict (0 captured, 1 selector never appeared / page unreachable), which is exactly
# what a boil milestone `check` for a UI box needs — and the PNG is the demo artifact.
#
# Idempotent. Installs the prebuilt binary into ~/.local/bin, writes a Chrome launcher that
# works on hosts where unprivileged user namespaces are restricted (Ubuntu 24.04 AppArmor:
# stock Chrome aborts with "No usable sandbox!"), registers the stdio MCP server for Claude
# Code (user scope) and Codex, then proves the CLI path against a local page.
#
#   sh <skill>/scripts/boil-iris-setup.sh            # install + register + smoke test
#   IRIS_CHROME_BIN=/usr/bin/google-chrome sh …      # pick the browser explicitly
#   sh … --smoke-url http://127.0.0.1:3000            # smoke-test against your dev server
set -eu

BIN="${IRIS_BIN_DIR:-$HOME/.local/bin}"
SMOKE_URL="https://example.com"
while [ $# -gt 0 ]; do
  case "$1" in
    --smoke-url) SMOKE_URL="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
mkdir -p "$BIN"

# 1. the binary (prebuilt; `cargo install iris-screenshot` when a Rust toolchain is preferred)
if ! command -v iris >/dev/null 2>&1 && [ ! -x "$BIN/iris" ]; then
  curl -fsSL https://raw.githubusercontent.com/brijr/iris/main/install.sh | IRIS_INSTALL_DIR="$BIN" sh
fi
IRIS="$(command -v iris 2>/dev/null || echo "$BIN/iris")"
echo "iris: $("$IRIS" --version)"

# 2. a Chrome-family browser. Prefer a system one; fall back to Playwright's bundled Chromium.
CHROME_BIN="${IRIS_CHROME_BIN:-}"
if [ -z "$CHROME_BIN" ]; then
  for c in google-chrome google-chrome-stable chromium chromium-browser brave-browser microsoft-edge; do
    if command -v "$c" >/dev/null 2>&1; then CHROME_BIN="$(command -v "$c")"; break; fi
  done
fi
if [ -z "$CHROME_BIN" ]; then
  CHROME_BIN="$(ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | sort -V | tail -1 || true)"
fi
if [ -z "$CHROME_BIN" ] || [ ! -x "$CHROME_BIN" ]; then
  echo "no Chrome-family browser found: install one, or run 'npx playwright install chromium', then re-run" >&2
  exit 1
fi

# 3. the launcher — `--no-sandbox` only where the kernel forbids Chrome's own sandbox.
WRAPPER="$BIN/iris-chrome"
NOSANDBOX=""
if [ "$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)" = "1" ]; then
  NOSANDBOX="--no-sandbox"
fi
cat > "$WRAPPER" <<EOF
#!/bin/sh
# Chrome launcher for iris, written by boil-iris-setup.sh — re-run that script to change it.
exec "\${IRIS_CHROME_BIN:-$CHROME_BIN}" $NOSANDBOX --disable-dev-shm-usage "\$@"
EOF
chmod +x "$WRAPPER"
echo "chrome: $CHROME_BIN ${NOSANDBOX:+(sandbox disabled: unprivileged userns restricted)}"

# 4. register the MCP server wherever an agent CLI is present (re-registering is idempotent)
if command -v claude >/dev/null 2>&1; then
  claude mcp remove -s user iris >/dev/null 2>&1 || true
  claude mcp add -s user iris -e "CHROME=$WRAPPER" -- "$IRIS" mcp >/dev/null
  echo "claude: iris registered (user scope)"
fi
if command -v codex >/dev/null 2>&1; then
  codex mcp remove iris >/dev/null 2>&1 || true
  codex mcp add iris --env "CHROME=$WRAPPER" -- "$IRIS" mcp >/dev/null
  echo "codex: iris registered"
fi

# 5. prove the CLI path (the MCP path uses the same engine and the same CHROME)
OUT="${TMPDIR:-/tmp}/iris-smoke-$$.png"
if CHROME="$WRAPPER" "$IRIS" "$SMOKE_URL" --scale 1 --json -o "$OUT" >/dev/null 2>&1 && [ -s "$OUT" ]; then
  echo "smoke: ok ($SMOKE_URL → $OUT)"; rm -f "$OUT"
else
  echo "smoke: FAILED for $SMOKE_URL — try --smoke-url against a local page; external sites can be slow or walled" >&2
  exit 1
fi
