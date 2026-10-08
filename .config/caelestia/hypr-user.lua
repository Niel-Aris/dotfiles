
-- Send the active window to the other monitor (second monitor DP-2 is on the left)
-- Overrides the default SUPER + left/right focus binds from hyprland/keybinds.lua
hl.unbind("SUPER + left")
hl.unbind("SUPER + right")
hl.bind("SUPER + left", hl.dsp.window.move({ monitor = "l", follow = true }))
hl.bind("SUPER + right", hl.dsp.window.move({ monitor = "r", follow = true }))
