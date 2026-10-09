
-- Send the active window to the other monitor (second monitor DP-2 is on the left)
-- Overrides the default SUPER + left/right focus binds from hyprland/keybinds.lua
hl.unbind("SUPER + left")
hl.unbind("SUPER + right")
hl.bind("SUPER + left", hl.dsp.window.move({ monitor = "l", follow = true }))
hl.bind("SUPER + right", hl.dsp.window.move({ monitor = "r", follow = true }))

-- Pomodoro: SUPER + P toggles the popup; the daemon runs in the background from login
-- (app: ~/.local/share/pomodoro, CLI: ~/.local/bin/pomodoro)
hl.bind("SUPER + P", hl.dsp.exec_cmd("pomodoro toggle"))
hl.window_rule({ match = { class = "org.lynx.Pomodoro" }, float = true, center = true, opacity = "1.0 override" })
hl.on("hyprland.start", function()
    hl.exec_cmd("pomodoro daemon")
end)
