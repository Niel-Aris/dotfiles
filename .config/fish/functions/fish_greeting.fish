function fish_greeting
    echo -ne '\x1b[38;5;16m'  # Set colour to primary
    echo '    __                     '
    echo '   / /   __  ______  _  __ '
    echo '  / /   / / / / __ \| |/_/ '
    echo ' / /___/ /_/ / / / />  <   '
    echo '/_____/\__, /_/ /_/_/|_|   '
    echo '      /____/               '
    set_color normal
    command -v fastfetch &> /dev/null && fastfetch --key-padding-left 5
end
