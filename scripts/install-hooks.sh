#!/bin/bash
# Установка git pre-commit hook для проверки приватных ключей
# Запуск: bash scripts/install-hooks.sh

HOOK=".git/hooks/pre-commit"

cat > "$HOOK" << 'EOF'
#!/bin/bash

if git diff --cached --name-only | grep -qE "\.(pem|key|p12|pfx|der)$"; then
    echo "❌ Попытка закоммитить файл с ключом!"
    echo "Удали из staging: git reset HEAD <файл>"
    exit 1
fi

if git diff --cached | grep -qE "BEGIN (RSA PRIVATE|EC PRIVATE|PRIVATE KEY)"; then
    echo "❌ Найден приватный ключ в содержимом файла!"
    exit 1
fi

if git diff --cached | grep -qiE "(password|secret|api_key)\s*=\s*['\"][^'\"]+['\"]" | grep -v "test\|example\|fixture"; then
    echo "⚠️ Возможен hardcoded secret — проверь перед коммитом"
fi

echo "✅ Проверка безопасности пройдена"
exit 0
EOF

chmod +x "$HOOK"
echo "✅ Pre-commit hook установлен: $HOOK"
