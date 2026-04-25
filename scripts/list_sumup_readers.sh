#!/bin/bash
# Lists all SumUp card readers for the configured merchant account.
# Usage: ./scripts/list_sumup_readers.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config/config.json"

if ! command -v jq &> /dev/null; then
    echo "❌ jq is required. Install with: brew install jq"
    exit 1
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ config/config.json not found"
    exit 1
fi

API_KEY=$(jq -r '.sumup_api_key // ""' "$CONFIG_FILE")
MERCHANT_CODE=$(jq -r '.sumup_merchant_code // ""' "$CONFIG_FILE")

if [ -z "$API_KEY" ] || [ "$API_KEY" = "null" ]; then
    echo "❌ sumup_api_key not set in config/config.json"
    exit 1
fi

if [ -z "$MERCHANT_CODE" ] || [ "$MERCHANT_CODE" = "null" ]; then
    echo "❌ sumup_merchant_code not set in config/config.json"
    exit 1
fi

echo "🔍 Fetching readers for merchant: $MERCHANT_CODE"
echo ""

BODY_FILE=$(mktemp)
HTTP_CODE=$(curl -s -o "$BODY_FILE" -w "%{http_code}" \
    -H "Authorization: Bearer $API_KEY" \
    "https://api.sumup.com/v0.1/merchants/$MERCHANT_CODE/readers")
BODY=$(cat "$BODY_FILE")
rm -f "$BODY_FILE"

if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ API error (HTTP $HTTP_CODE):"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
    exit 1
fi

COUNT=$(echo "$BODY" | jq '. | if type == "array" then length else .items | length end' 2>/dev/null)

if [ "$COUNT" = "0" ] || [ -z "$COUNT" ]; then
    echo "⚠️  No readers found for this merchant."
    exit 0
fi

echo "Found $COUNT reader(s):"
echo ""

echo "$BODY" | jq -r '
  (if type == "array" then . else .items end) |
  .[] |
  "  ID:     \(.id)\n  Name:   \(.name // "—")\n  Status: \(.status // "—")\n  Serial: \(.serial_number // "—")\n"
'

echo ""
echo "💡 To set a reader, update sumup_reader_id in config/config.json:"
echo "   \"sumup_reader_id\": \"<id from above>\""
