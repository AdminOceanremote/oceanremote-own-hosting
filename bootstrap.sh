#!/usr/bin/env bash
set -e

echo "=== OceanRemote Own-Hosting Setup ==="
echo

# Load virtualenvwrapper if available (PythonAnywhere)
if [ -f "$HOME/.local/bin/virtualenvwrapper.sh" ]; then
    source "$HOME/.local/bin/virtualenvwrapper.sh"
elif [ -f "/usr/local/bin/virtualenvwrapper.sh" ]; then
    source "/usr/local/bin/virtualenvwrapper.sh"
fi

if [ ! -f "manage.py" ]; then
    echo "Cloning repo..."
    git clone https://github.com/AdminOceanremote/oceanremote-own-hosting.git
    cd oceanremote-own-hosting
fi

VENV="$HOME/.virtualenvs/oceanremote-env"
if [ ! -d "$VENV" ]; then
    echo "Creating virtualenv at $VENV ..."
    if command -v mkvirtualenv >/dev/null 2>&1; then
        mkvirtualenv --python=/usr/bin/python3.10 oceanremote-env
    else
        python3.10 -m venv "$VENV"
    fi
fi

source "$VENV/bin/activate"
echo "Activated: $(which python)"

echo "Installing requirements..."
pip install -q -r requirements.txt

echo
python wizard.py