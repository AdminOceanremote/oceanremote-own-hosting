#!/usr/bin/env bash
set -e

C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_RED="\033[1;31m"
C_DIM="\033[2m"
C_RESET="\033[0m"

echo -e "${C_CYAN}"
echo "  =========================================================="
echo "          OceanRemote Own-Hosting Setup Wizard"
echo "          Cold-chain monitoring on PythonAnywhere"
echo "  =========================================================="
echo -e "${C_RESET}"

echo -e "${C_YELLOW}This setup runs automatically. Total time: 1-3 minutes.${C_RESET}"
echo -e "${C_YELLOW}Do NOT close this console while it is running.${C_RESET}"
echo

if [ -z "$API_TOKEN" ]; then
    echo -e "${C_RED}API_TOKEN is not set.${C_RESET}"
    echo -e "  1. Go to PythonAnywhere -> Account -> API Token -> Create new API token"
    echo -e "  2. Close this console, open a NEW Bash console, and run this script again."
    exit 1
fi

if [ -f "$HOME/.local/bin/virtualenvwrapper.sh" ]; then
    source "$HOME/.local/bin/virtualenvwrapper.sh"
elif [ -f "/usr/local/bin/virtualenvwrapper.sh" ]; then
    source "/usr/local/bin/virtualenvwrapper.sh"
fi

if [ ! -f "manage.py" ]; then
    echo -e "${C_CYAN}[1/3] Cloning repository...${C_RESET}"
    git clone https://github.com/AdminOceanremote/oceanremote-own-hosting.git
    cd oceanremote-own-hosting
else
    echo -e "${C_CYAN}[1/3] Repository already present.${C_RESET}"
fi

VENV="$HOME/.virtualenvs/oceanremote-env"
if [ ! -d "$VENV" ]; then
    echo -e "${C_CYAN}[2/3] Creating virtualenv at $VENV ...${C_RESET}"
    if command -v mkvirtualenv >/dev/null 2>&1; then
        mkvirtualenv --python=/usr/bin/python3.10 oceanremote-env
    else
        python3.10 -m venv "$VENV"
    fi
else
    echo -e "${C_CYAN}[2/3] Virtualenv already exists.${C_RESET}"
fi

source "$VENV/bin/activate"
echo -e "${C_GREEN}Activated: $(which python)${C_RESET}"

echo
echo -e "${C_YELLOW}[3/3] Installing requirements...${C_RESET}"
echo -e "${C_DIM}This step downloads ~15 packages and may take 1-3 minutes.${C_RESET}"
echo -e "${C_DIM}You will see package names scrolling - that is normal.${C_RESET}"
echo -e "${C_DIM}Do NOT close this console until you see 'Setup complete'.${C_RESET}"
echo
sleep 2

START=$(date +%s)
pip install --progress-bar on -r requirements.txt
END=$(date +%s)

echo
echo -e "${C_GREEN}Requirements installed in $((END-START))s.${C_RESET}"
echo

echo -e "${C_CYAN}Starting wizard (3 prompts)...${C_RESET}"
echo
python wizard.py

echo
echo -e "${C_GREEN}Setup complete. Your server is live.${C_RESET}"