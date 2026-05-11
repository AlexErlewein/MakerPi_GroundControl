#!/bin/bash
# Inject custom CSS into Planka's index.html

# Wait for Planka to be ready
sleep 5

# Get the current index.html and inject our CSS
INDEX_FILE="/app/public/index.html"

if [ -f "$INDEX_FILE" ]; then
    # Backup original
    cp "$INDEX_FILE" "${INDEX_FILE}.backup"
    
    # Inject custom CSS link before </head>
    sed -i 's|</head>|<link rel="stylesheet" href="/custom.css">\n</head>|g' "$INDEX_FILE"
    
    echo "Custom CSS injected into index.html"
else
    echo "index.html not found at $INDEX_FILE"
    # Find where index.html is
    find /app -name "index.html" -type f 2>/dev/null
fi
