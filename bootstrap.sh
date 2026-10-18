#!/usr/bin/env bash
# OceanRemote Own-Hosting bootstrap
set -e

echo "=== OceanRemote Own-Hosting Setup ==="
echo

# 1. Clone if not already inside the repo
if [ ! -f "manage.py" ]; then
    echo "Cloning repo..."
    git clone https://github.com/AdminOceanremote/oceanremote-own-hosting.git
    cd oceanremote-own-hosting
else
    echo "Already inside repo."
fi

# 2. Create virtualenv if missing
if [ ! -d "$HOME/.virtualenvs/oceanremote-env" ]; then
    echo "Creating virtualenv..."
    mkvirtualenv --python=/usr/bin/python3.10 oceanremote-env
fi
source "$HOME/.virtualenvs/oceanremote-env/bin/activate"

# 3. Install deps
echo "Installing requirements..."
pip install -q -r requirements.txt

# 4. Run wizard
echo
python wizard.py