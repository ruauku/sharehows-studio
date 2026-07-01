#!/bin/zsh
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "Python3가 설치되어 있지 않습니다. python.org에서 Python을 먼저 설치해주세요." buttons {"확인"} default button 1'
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml <<'EOF'
[general]
email = ""
EOF

python3 -m pip install --user -r requirements.txt
python3 -m streamlit run app.py --browser.gatherUsageStats false
