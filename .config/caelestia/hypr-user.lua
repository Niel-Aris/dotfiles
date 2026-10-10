
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

-- Obsidian: slightly more see-through than the global windowOpacity (0.95)
hl.window_rule({ match = { class = "md.obsidian.Obsidian" }, opacity = "0.9 override" })

-- Zen: fully opaque, overriding the global windowOpacity (0.95)
hl.window_rule({ match = { class = "zen" }, opacity = "1.0 override" })
hl.on("hyprland.start", function()
    hl.exec_cmd("pomodoro daemon")
end)

-- Mouse side buttons step through Zen tabs (Ctrl+PgUp / Ctrl+PgDn).
-- Up button (mouse:276, forward) = previous tab, down button (mouse:275, back) = next tab.
-- Outside Zen the button is passed through to the focused window unchanged.
local function zen_tab_button(button, key)
    hl.bind(button, function()
        local win = hl.get_active_window()
        if not win then return end

        if win.class == "zen" then
            hl.dispatch(hl.dsp.send_shortcut({ mods = "CTRL", key = key, window = "address:" .. win.address }))
        else
            hl.dispatch(hl.dsp.pass({ window = "address:" .. win.address }))
        end
    end, { mouse = true })
end

zen_tab_button("mouse:276", "Page_Up")
zen_tab_button("mouse:275", "Page_Down")
