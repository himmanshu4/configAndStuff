# Oh My Zsh Setup
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git)
source $ZSH/oh-my-zsh.sh

# User Path Configuration (Generic)
export PATH="$HOME/.local/bin:$HOME/bin:$PATH"

# Initialize Starship Prompt
eval "$(starship init zsh)"
