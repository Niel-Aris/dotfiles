function uxplay --wraps uxplay --description 'UxPlay with lynux settings (fixed ports, 11in iPad resolution, fullscreen)'
    command uxplay -n lynux-pc -nh -p 7000 -s 2388x1668@60 -fs $argv
end
