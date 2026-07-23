#!/bin/bash

# Get the absolute path of this repository
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_CONFIG_DIR="$HOME/.config/configAndStuff"

# Ensure the local config folder exists
mkdir -p "$LOCAL_CONFIG_DIR"

echo "Setting up dotfiles..."

# Map of repository files to their target installation paths
# Syntax: ["repo_file"]="target_path"
declare -A CONFIG_MAP=(
    ["zshrc"]="$HOME/.zshrc"
    ["starship.toml"]="$HOME/.config/starship.toml"
    ["systemd/user/kitty-theme@.service"]="$HOME/.config/systemd/user/kitty-theme@.service"
    ["systemd/user/kitty-theme-day.timer"]="$HOME/.config/systemd/user/kitty-theme-day.timer"
    ["systemd/user/kitty-theme-night.timer"]="$HOME/.config/systemd/user/kitty-theme-night.timer"
    # Examples of how to add more tools in the future:
    # ["vimrc"]="$HOME/.vimrc"
    # ["nvim/init.lua"]="$HOME/.config/nvim/init.lua"
    # ["tmux.conf"]="$HOME/.tmux.conf"
)

for REPO_FILE in "${!CONFIG_MAP[@]}"; do
    TARGET="${CONFIG_MAP[$REPO_FILE]}"
    TARGET_DIR="$(dirname "$TARGET")"
    
    # Create the target directory if it doesn't already exist (e.g. for ~/.config/nvim/)
    mkdir -p "$TARGET_DIR"

    # Create a safe filename for the local overrides (replaces / with _ so "nvim/init.lua" becomes "nvim_init.lua.begin")
    LOCAL_PREFIX="${REPO_FILE//\//_}"
    
    # Ensure local placeholder files exist so they are easy to discover
    touch "$LOCAL_CONFIG_DIR/${LOCAL_PREFIX}.begin" "$LOCAL_CONFIG_DIR/${LOCAL_PREFIX}.end"
    
    echo "Building $TARGET..."
    
    # Backup existing file if it exists
    if [ -f "$TARGET" ] || [ -L "$TARGET" ]; then
        mv "$TARGET" "${TARGET}.old"
    fi
    
    # Clear or create the target file
    > "$TARGET"
    
    # 1. Append the .begin file (if it has content)
    if [ -s "$LOCAL_CONFIG_DIR/${LOCAL_PREFIX}.begin" ]; then
        cat "$LOCAL_CONFIG_DIR/${LOCAL_PREFIX}.begin" >> "$TARGET"
        echo -e "\n" >> "$TARGET"
    fi
    
    # 2. Append the main tracked file (if it exists)
    if [ -f "$DIR/$REPO_FILE" ]; then
        cat "$DIR/$REPO_FILE" >> "$TARGET"
        echo -e "\n" >> "$TARGET"
    fi
    
    # 3. Append the .end file (if it has content)
    if [ -s "$LOCAL_CONFIG_DIR/${LOCAL_PREFIX}.end" ]; then
        cat "$LOCAL_CONFIG_DIR/${LOCAL_PREFIX}.end" >> "$TARGET"
        echo -e "\n" >> "$TARGET"
    fi
done

echo "Done!"
echo "Note: Since files are concatenated, remember to re-run 'bash setup.sh' if you update your tracked config files."
