# VIM CHEATSHEET   (q = close · / = search · zR/zM = unfold/fold all)
Leader = <Space>. Inside Vim, <Space>? reopens this.

## 1. MY CUSTOM KEYBINDS (from ~/.vimrc)
### Files / navigation
| Key            | Action                                  |
|----------------|-----------------------------------------|
| Ctrl+B         | Toggle file explorer (NERDTree)         |
| Space e        | Reveal current file in explorer         |
| Ctrl+P         | Fuzzy find files                        |
| Ctrl+F         | Search text in project (ripgrep)        |
| Space b        | Pick open buffer                        |
| Space g        | Changed git files                       |
| Tab / S-Tab    | Next / previous buffer ("tab")          |
| Ctrl+W x       | Close buffer                            |
| Ctrl+\         | Open terminal split (Esc Esc to leave)  |
### Editing
| Key            | Action                                  |
|----------------|-----------------------------------------|
| Ctrl+S / Space w | Save                                  |
| Ctrl+Q         | Quit window                             |
| Ctrl+/         | Comment line / selection                |
| Alt+J / Alt+K  | Move line (or selection) down / up      |
| < / > (visual) | Indent and keep selection               |
| Esc Esc        | Clear search highlight                  |
| Tab / S-Tab (insert) | Next / prev completion item       |
| Enter (popup)  | Accept completion                       |
### LSP (code intelligence)
| Key            | Action                                  |
|----------------|-----------------------------------------|
| gd / gD        | Go to definition / declaration          |
| gi             | Go to implementation                    |
| gr             | Show references                         |
| K              | Hover docs                              |
| Ctrl+K         | Signature help                          |
| F2             | Rename symbol                           |
| Space ca       | Code action                             |
| Space f        | Format document                         |
| Space o        | Document symbols (outline)              |
| Space d        | Diagnostics for current line            |
| ]d / [d        | Next / previous diagnostic              |
### Plugin-provided
| Key            | Action                                  |
|----------------|-----------------------------------------|
| gcc / gc{motion} | Comment (vim-commentary)              |
| ys{motion}{c}  | Surround with c (vim-surround)          |
| cs"'  / ds"    | Change / delete surrounding             |
| S{c} (visual)  | Surround selection                      |
| ]c / [c        | Next / prev git hunk (gitgutter)        |
| Space h s/u/p  | (gitgutter default: <leader>hs stage hunk, hu undo, hp preview) |
| :Git           | Fugitive git status                     |
| Space (wait)   | Which-key popup with all leader maps    |
| :PlugUpdate    | Update plugins                          |

## 2. MODES
| Key        | Action                          |
|------------|---------------------------------|
| i / a      | Insert before / after cursor    |
| I / A      | Insert at line start / end      |
| o / O      | New line below / above          |
| v / V      | Visual char / line              |
| Ctrl+V     | Visual block                    |
| R          | Replace mode                    |
| Esc / Ctrl+[ | Back to normal                |
| :          | Command line                    |

## 3. MOTIONS
### Basic
| Key        | Motion                          |
|------------|---------------------------------|
| h j k l    | Left / down / up / right        |
| w / W      | Next word start / WORD          |
| b / B      | Previous word start / WORD      |
| e / E      | Word end                        |
| ge         | Previous word end               |
| 0 / ^ / $  | Line start / first char / end   |
| g_         | Last non-blank char             |
| gg / G     | File top / bottom               |
| {n}G / :n  | Go to line n                    |
| % (on bracket) | Jump to matching bracket    |
| { / }      | Previous / next paragraph       |
| ( / )      | Previous / next sentence        |
| H / M / L  | Top / middle / bottom of screen |
| Ctrl+D / Ctrl+U | Half page down / up        |
| Ctrl+F / Ctrl+B | (overridden by my maps)    |
| zz / zt / zb | Center / top / bottom cursor line |
### Find on line / search
| Key        | Motion                          |
|------------|---------------------------------|
| f{c} / F{c}| Jump to char forward / back     |
| t{c} / T{c}| Jump till char forward / back   |
| ; / ,      | Repeat / reverse last f,t,F,T   |
| /pat  ?pat | Search forward / backward       |
| n / N      | Next / previous match           |
| * / #      | Search word under cursor fwd / back |
### Jumps and marks
| Key        | Motion                          |
|------------|---------------------------------|
| Ctrl+O / Ctrl+I | Jump back / forward in jumplist |
| `` / ''    | Return to previous position     |
| m{a-z}     | Set mark                        |
| `{a-z} / '{a-z} | Jump to mark exact / line  |
| g; / g,    | Older / newer change position   |
| gi         | (overridden by LSP in code files) |

## 4. OPERATORS (combine with motions: operator + motion)
| Key  | Action                | Example                         |
|------|-----------------------|---------------------------------|
| d    | Delete (cut)          | dw, d$, dG, d2j                 |
| c    | Change (delete+insert)| cw, c$, ci"                     |
| y    | Yank (copy)           | yy, yw, y$                      |
| >  < | Indent / outdent      | >>, >ip                         |
| =    | Auto-indent           | ==, =G                          |
| gu / gU | Lower / UPPER case | guiw, gUU                       |
| g~   | Toggle case           | g~w                             |
| gq   | Format/wrap text      | gqip                            |
| !    | Filter through command| !ip sort                        |
Doubled operator = whole line: dd, yy, cc, >>, gUU.
Shortcuts: D = d$, C = c$, Y = yy, x = dl, X = dh, s = cl, S = cc.

## 5. TEXT OBJECTS (use after d/c/y/v; i = inner, a = around)
| Object     | Meaning                         |
|------------|---------------------------------|
| iw / aw    | Word                            |
| iW / aW    | WORD                            |
| is / as    | Sentence                        |
| ip / ap    | Paragraph                       |
| i" / a"  i' i`  | Quoted string               |
| i( / ib / a(  | Parentheses                  |
| i{ / iB / a{  | Braces                       |
| i[ / a[    | Brackets                        |
| i< / a<    | Angle brackets                  |
| it / at    | HTML/XML tag                    |
Examples: ci" change inside quotes · da( delete parens incl. · yit yank tag contents · vip select paragraph.

## 6. EDITING & REGISTERS
| Key        | Action                          |
|------------|---------------------------------|
| u / Ctrl+R | Undo / redo                     |
| .          | Repeat last change              |
| p / P      | Paste after / before            |
| "{r}y / "{r}p | Use register r             |
| "+y / "+p  | System clipboard                |
| "0p        | Paste last yank (not delete)    |
| :reg       | List registers                  |
| J / gJ     | Join lines (with / without space) |
| r{c}       | Replace one char                |
| ~          | Toggle case of char             |
| Ctrl+A / Ctrl+X | Increment / decrement number |
| {n}{cmd}   | Repeat count: 5dd, 3p, 10j      |
### Macros
| Key        | Action                          |
|------------|---------------------------------|
| q{r}       | Start recording into r          |
| q          | Stop recording                  |
| @{r} / @@  | Play macro / repeat last        |
| {n}@{r}    | Play n times                    |
### Insert-mode shortcuts
| Key        | Action                          |
|------------|---------------------------------|
| Ctrl+W     | Delete word back                |
| Ctrl+U     | Delete to line start            |
| Ctrl+R {r} | Insert register                 |
| Ctrl+O     | Run one normal-mode command     |
| Ctrl+N / Ctrl+P | Keyword completion          |

## 7. VISUAL MODE
| Key        | Action                          |
|------------|---------------------------------|
| o          | Jump to other end of selection  |
| gv         | Reselect last selection         |
| I / A (block) | Insert / append on all lines |
| $ (block)  | Extend block to line ends       |
| :          | Run command on selection        |
| u / U / ~  | Lower / upper / toggle case     |

## 8. SEARCH & REPLACE
| Command            | Action                          |
|--------------------|---------------------------------|
| :s/old/new/        | Replace first on line           |
| :s/old/new/g       | All on line                     |
| :%s/old/new/g      | All in file                     |
| :%s/old/new/gc     | All, confirm each               |
| :'<,'>s/old/new/g  | In visual selection             |
| :g/pat/d           | Delete lines matching           |
| :v/pat/d           | Delete lines NOT matching       |
| :g/pat/normal @q   | Run macro on matching lines     |
| \v prefix          | "Very magic" regex              |
| :noh               | Clear highlight                 |

## 9. WINDOWS, BUFFERS, TABS
| Key / Command | Action                       |
|---------------|------------------------------|
| :sp / :vsp    | Horizontal / vertical split  |
| Ctrl+W h/j/k/l| Move between splits          |
| Ctrl+W = / _ / \| | Equalize / max height / max width |
| Ctrl+W c / o  | Close / keep only this       |
| Ctrl+W r / x  | Rotate / exchange (note: my Ctrl+W x closes buffer) |
| :ls           | List buffers                 |
| :b {name/num} | Switch buffer                |
| :bd           | Delete buffer                |
| :tabnew / gt / gT | Tab page new / next / prev |
| :e file       | Edit file                    |
| :e!           | Discard changes, reload      |

## 10. FILES & COMMANDS
| Command         | Action                       |
|-----------------|------------------------------|
| :w / :q / :wq   | Write / quit / both          |
| :q! / :wa / :qa | Force quit / write all / quit all |
| :x or ZZ        | Save and quit                |
| ZQ              | Quit without saving          |
| :w !sudo tee %  | Save as root                 |
| :r file / :r !cmd | Insert file / command output |
| :!cmd           | Run shell command            |
| :terminal       | Terminal in a window         |
| :help {topic}   | Built-in help (Ctrl+] follows tag) |
| q:              | Command-line history window  |

## 11. FOLDING
| Key  | Action                | Key  | Action               |
|------|-----------------------|------|----------------------|
| za   | Toggle fold           | zR   | Open all             |
| zo/zc| Open / close          | zM   | Close all            |
| zf{m}| Create fold           | zd   | Delete fold          |
