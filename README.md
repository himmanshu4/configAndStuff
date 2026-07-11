# configAndStuff

A personal repository for tracking dotfiles and system configurations.

## Architecture

This setup uses a robust **file concatenation** approach instead of standard symlinking. This gives you the power of a single source of truth in your git repository, while allowing for machine-specific overrides that remain untracked.

When you run `setup.sh`, it reads the `CONFIG_MAP` and processes each file as follows:
1. It prepends any machine-specific `.begin` overrides.
2. It appends the main tracked configuration from this repository.
3. It appends any machine-specific `.end` overrides.
4. It compiles them together into the final destination (e.g., `~/.zshrc`).

### Adding New Configurations
To add a new tool (like Vim or Tmux), edit the `CONFIG_MAP` associative array in `setup.sh`:

```bash
declare -A CONFIG_MAP=(
    ["zshrc"]="$HOME/.zshrc"
    ["vimrc"]="$HOME/.vimrc"
    ["nvim/init.lua"]="$HOME/.config/nvim/init.lua"
)
```

## Machine-Specific Overrides (Untracked)

Not all machines are identical. You might have work-specific aliases or environment variables that shouldn't be tracked in version control. 

This repository supports local overrides using the XDG Base Directory Specification. When `setup.sh` runs, it will look inside `~/.config/configAndStuff/` for `.begin` and `.end` files corresponding to your configurations. 

For example, to add an alias only on your current machine, you would add it to:
`~/.config/configAndStuff/zshrc.end`

*(Note: If a mapped configuration file is nested like `nvim/init.lua`, its local overrides are safely flattened to `nvim_init.lua.begin`.)*

## Setup Instructions

Simply run the setup script from the root of this repository to compile and install your configurations:

```bash
bash setup.sh
```

**⚠️ Important:** Because this setup uses file concatenation, you must remember to re-run `bash setup.sh` whenever you edit the tracked config files inside this repository to recompile the changes!
