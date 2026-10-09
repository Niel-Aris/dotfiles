" ~/.vimrc — VSCode-like Vim: LSP, file tree, fuzzy finder, git, pretty UI
set nocompatible
let mapleader = " "

" ---------- Plugins ----------
call plug#begin('~/.vim/plugged')
Plug 'catppuccin/vim', { 'as': 'catppuccin' }     " theme
Plug 'itchyny/lightline.vim'                      " status line
Plug 'mengelbrecht/lightline-bufferline'          " tabs-style buffer bar
Plug 'ryanoasis/vim-devicons'                     " file icons (Nerd Font)
Plug 'preservim/nerdtree'                         " explorer sidebar
Plug 'Xuyuanp/nerdtree-git-plugin'
Plug 'tiagofumo/vim-nerdtree-syntax-highlight'
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'                           " Ctrl+P / ripgrep search
Plug 'airblade/vim-gitgutter'                     " git diff in gutter
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-commentary'                       " gc to comment
Plug 'tpope/vim-surround'
Plug 'jiangmiao/auto-pairs'
Plug 'Yggdroot/indentLine'                        " indent guides
Plug 'sheerun/vim-polyglot'                       " syntax for everything
Plug 'liuchengxu/vim-which-key'                   " keybinding hints
Plug 'mhinz/vim-startify'                         " start screen
Plug 'yegappan/lsp'                               " native LSP client (no node needed)
call plug#end()

" ---------- Basics ----------
syntax on
filetype plugin indent on
set encoding=utf-8
set number relativenumber cursorline signcolumn=yes
set mouse=a ttymouse=sgr
set clipboard=unnamedplus
set hidden autoread updatetime=300 timeoutlen=500 ttimeoutlen=10
set expandtab shiftwidth=4 tabstop=4 smartindent
set ignorecase smartcase incsearch hlsearch
set scrolloff=8 splitright splitbelow wrap linebreak
set noshowmode laststatus=2 showtabline=2
set wildmenu wildoptions=pum completeopt=menuone,noselect,popup
set undofile undodir=~/.vim/undo
set noswapfile nobackup
set list listchars=tab:»\ ,trail:·
if !isdirectory(expand('~/.vim/undo')) | call mkdir(expand('~/.vim/undo'), 'p') | endif

" ---------- Theme ----------
if has('termguicolors')
  let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"
  let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"
  set termguicolors
endif
set background=dark
silent! colorscheme catppuccin_mocha
let g:lightline = {
  \ 'colorscheme': 'catppuccin_mocha',
  \ 'active': { 'left': [['mode','paste'],['branch','readonly','filename','modified']] },
  \ 'tabline': { 'left': [['buffers']], 'right': [['close']] },
  \ 'component_expand': { 'buffers': 'lightline#bufferline#buffers' },
  \ 'component_type': { 'buffers': 'tabsel' },
  \ 'component_function': { 'branch': 'FugitiveHead' },
  \ 'separator': { 'left': "", 'right': "" },
  \ 'subseparator': { 'left': "", 'right': "" },
  \ }
let g:lightline#bufferline#show_number = 2
let g:lightline#bufferline#enable_devicons = 1
let g:indentLine_char = '│'
let g:indentLine_fileTypeExclude = ['startify', 'nerdtree', 'help', 'json', 'markdown']
let g:startify_custom_header = []
let g:WebDevIconsUnicodeDecorateFolderNodes = 1
let g:gitgutter_sign_added = '▎' | let g:gitgutter_sign_modified = '▎' | let g:gitgutter_sign_removed = '▁'

" ---------- Explorer (Ctrl+B like VSCode) ----------
let NERDTreeMinimalUI = 1
let NERDTreeShowHidden = 1
let NERDTreeIgnore = ['\.git$', '__pycache__']
nnoremap <C-b> :NERDTreeToggle<CR>
nnoremap <leader>e :NERDTreeFind<CR>
autocmd BufEnter * if winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() | quit | endif

" ---------- Fuzzy finding ----------
let $FZF_DEFAULT_COMMAND = 'fd --type f --hidden --exclude .git'
nnoremap <C-p> :Files<CR>
nnoremap <C-f> :Rg<CR>
nnoremap <leader>b :Buffers<CR>
nnoremap <leader>g :GFiles?<CR>

" ---------- Buffers as tabs ----------
nnoremap <Tab> :bnext<CR>
nnoremap <S-Tab> :bprevious<CR>
nnoremap <C-w>x :bdelete<CR>
nnoremap <leader>w :w<CR>
nnoremap <C-s> :w<CR>
inoremap <C-s> <Esc>:w<CR>a
nnoremap <C-q> :q<CR>
nnoremap <Esc><Esc> :nohlsearch<CR>
vnoremap < <gv
vnoremap > >gv
nnoremap <A-j> :m .+1<CR>==
nnoremap <A-k> :m .-2<CR>==
vnoremap <A-j> :m '>+1<CR>gv=gv
vnoremap <A-k> :m '<-2<CR>gv=gv
nnoremap <C-_> :Commentary<CR>
vnoremap <C-_> :Commentary<CR>
nnoremap <C-\> :terminal ++rows=15<CR>
tnoremap <Esc><Esc> <C-\><C-n>

" ---------- LSP ----------
let lspOpts = #{
  \ autoHighlightDiags: v:true,
  \ showDiagWithVirtualText: v:true,
  \ diagVirtualTextAlign: 'after',
  \ completionMatcher: 'fuzzy',
  \ autoComplete: v:true,
  \ showSignature: v:true,
  \ ignoreMissingServer: v:true,
  \ }
autocmd User LspSetup call LspOptionsSet(lspOpts)

let lspServers = [
  \ #{name: 'clangd',       filetype: ['c', 'cpp'],            path: 'clangd',  args: ['--background-index']},
  \ #{name: 'rust-analyzer', filetype: ['rust'],               path: 'rust-analyzer', args: [], syncInit: v:true},
  \ #{name: 'pyright',      filetype: ['python'],              path: 'pyright-langserver', args: ['--stdio']},
  \ #{name: 'tsserver',     filetype: ['javascript', 'typescript', 'javascriptreact', 'typescriptreact'], path: 'typescript-language-server', args: ['--stdio']},
  \ #{name: 'bashls',       filetype: ['sh', 'bash'],          path: 'bash-language-server', args: ['start']},
  \ #{name: 'gopls',        filetype: ['go'],                  path: 'gopls',   args: ['serve']},
  \ #{name: 'lua-ls',       filetype: ['lua'],                 path: 'lua-language-server', args: []},
  \ #{name: 'vimls',        filetype: ['vim'],                 path: 'vim-language-server', args: ['--stdio']},
  \ ]
autocmd User LspSetup call LspAddServer(lspServers)

function! s:LspMaps() abort
  nnoremap <buffer> gd <Cmd>LspGotoDefinition<CR>
  nnoremap <buffer> gD <Cmd>LspGotoDeclaration<CR>
  nnoremap <buffer> gi <Cmd>LspGotoImpl<CR>
  nnoremap <buffer> gr <Cmd>LspShowReferences<CR>
  nnoremap <buffer> K  <Cmd>LspHover<CR>
  nnoremap <buffer> <F2> <Cmd>LspRename<CR>
  nnoremap <buffer> <leader>ca <Cmd>LspCodeAction<CR>
  nnoremap <buffer> <leader>f <Cmd>LspFormat<CR>
  nnoremap <buffer> <leader>o <Cmd>LspDocumentSymbol<CR>
  nnoremap <buffer> <leader>d <Cmd>LspDiag current<CR>
  nnoremap <buffer> ]d <Cmd>LspDiag next<CR>
  nnoremap <buffer> [d <Cmd>LspDiag prev<CR>
  nnoremap <buffer> <C-k> <Cmd>LspShowSignature<CR>
endfunction
autocmd User LspAttached call s:LspMaps()

inoremap <expr> <Tab>   pumvisible() ? "\<C-n>" : "\<Tab>"
inoremap <expr> <S-Tab> pumvisible() ? "\<C-p>" : "\<S-Tab>"
inoremap <expr> <CR>    pumvisible() ? "\<C-y>" : "\<CR>"

" ---------- Which-key ----------
nnoremap <silent> <leader> :WhichKey '<Space>'<CR>
