#!/usr/bin/env bash
# Oracle: CLI React Hook Form example, then stub chat + stub submit.
# create --example with-react-hook-form currently fails shadcn's extra
# npm install (@hookform/resolvers vs zod 4). Gold retries with
# legacy-peer-deps. Documented in the G3 tracker.
set -euo pipefail
cd /workspace
npm config set legacy-peer-deps true
set +e
npx --yes assistant-ui@latest create gold-app \
  --example with-react-hook-form \
  --use-npm \
  --no-skills
create_ec=$?
set -e
if [ ! -d /workspace/gold-app ]; then
  echo "ERROR: assistant-ui create did not write gold-app" >&2
  exit 1
fi
printf 'legacy-peer-deps=true\n' >> /workspace/gold-app/.npmrc
if [ ! -f /workspace/gold-app/components/assistant-ui/thread.tsx ] && [ ! -f /workspace/gold-app/components/ui/thread.tsx ]; then
  (
    cd /workspace/gold-app
    npx --yes shadcn@latest add button card form input separator textarea resizable utils @assistant-ui/thread --yes
  )
fi
if [ "$create_ec" -ne 0 ] && [ ! -f /workspace/gold-app/components/ui/form.tsx ]; then
  echo "ERROR: shadcn components still missing after retry" >&2
  exit 1
fi

overlay="$(cd "$(dirname "$0")" && pwd)/overlay"
mkdir -p /workspace/gold-app/app/api/chat /workspace/gold-app/lib
cp "$overlay/app/api/chat/route.ts" \
  /workspace/gold-app/app/api/chat/route.ts
cp "$overlay/app/MyRuntimeProvider.tsx" \
  /workspace/gold-app/app/MyRuntimeProvider.tsx
if [ -f /workspace/gold-app/lib/submitSignup.tsx ]; then
  cp "$overlay/lib/submitSignup.tsx" /workspace/gold-app/lib/submitSignup.tsx
elif [ -f /workspace/gold-app/lib/submitSignup.ts ]; then
  cp "$overlay/lib/submitSignup.tsx" /workspace/gold-app/lib/submitSignup.ts
else
  cp "$overlay/lib/submitSignup.tsx" /workspace/gold-app/lib/submitSignup.tsx
fi
if [ -f "$overlay/.env.example" ]; then
  cp "$overlay/.env.example" /workspace/gold-app/.env.example
fi
