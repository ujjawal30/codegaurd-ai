#!/bin/sh
# Generate /env.js from VITE_* environment variables at container startup.
# This enables runtime configuration for the production Nginx container.

ENV_JS_PATH="/usr/share/nginx/html/env.js"

echo "window.__ENV__ = {" > "$ENV_JS_PATH"

# Iterate over all env vars starting with VITE_
env | grep '^VITE_' | while IFS='=' read -r key value; do
  echo "  \"$key\": \"$value\"," >> "$ENV_JS_PATH"
done

echo "};" >> "$ENV_JS_PATH"

echo "Generated $ENV_JS_PATH"
cat "$ENV_JS_PATH"

# Start Nginx
exec nginx -g "daemon off;"
