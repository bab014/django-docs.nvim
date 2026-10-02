# django-docs.nvim

Offline, ranked section search for locally built Django Markdown documentation.
Select a result to open the original file at its section heading. Uses
`vim.ui.select` and `vim.ui.input`; no picker plugin or AI service required.

Requires Neovim 0.10+ and Python 3 with SQLite FTS5. Documentation is supplied
separately. Releases, contributor internals, and the contribution tutorial are
excluded. This plugin makes no network requests.

## Install locally with lazy.nvim

```lua
{
  dir = '/home/bbeat/repos/django/build/markdown/docsearch/django-docs.nvim',
  name = 'django-docs.nvim',
  main = 'django_docs',
  cmd = { 'DjangoDocs', 'DjangoDocsIndex' },
  opts = {
    docs_path = '/home/bbeat/repos/django/build/markdown',
    python = 'python3',
    limit = 10,
  },
  keys = {
    { '<leader>dd', '<cmd>DjangoDocs<CR>', desc = 'Django documentation' },
  },
}
```

Remove the previous `dofile(.../docsearch/neovim.lua)` from your configuration.
Restart Neovim after switching to the plugin.

The plugin directory is self-contained and can be copied outside the docs build
output. Update `dir` to its new location. Once you publish that directory as a
Git repository, replace `dir` and `name` with your actual `"owner/django-docs.nvim"`
repository name in the plugin specification. No build hook is needed.

## Without a plugin manager

Place this directory under your Neovim data directory's
`site/pack/local/start/django-docs.nvim`, and configure it in `init.lua`:

```lua
require('django_docs').setup({
  docs_path = '/absolute/path/to/django/build/markdown',
})
vim.keymap.set('n', '<leader>dd', '<cmd>DjangoDocs<CR>')
```

## Commands

```vim
:DjangoDocs
:DjangoDocs how to build a model
:DjangoDocs template inheritance
:DjangoDocs ForeignKey on_delete
:DjangoDocsIndex
```

The first search builds the index asynchronously. The database lives in
Neovim's cache directory, keyed by the documentation path, not in the plugin or
docs directories. Run `:DjangoDocsIndex` after rebuilding or changing the docs.
Changing `docs_path` selects a separate index. Keep docs matched to your project's
Django version; the plugin does not check that version.

Search ranks headings, breadcrumbs, and section text using SQLite FTS5 BM25,
with stemming and a small alias list. Natural-language relevance is heuristic,
not semantic search. Try exact API names when results are too broad. Documentation
files that contain headings but no explanatory text remain searchable.

## CLI

```sh
python3 python/search.py --docs /path/to/markdown 'template inheritance'
python3 python/search.py --docs /path/to/markdown --index
```

Optional flags: `--json`, `--limit N`, `--open N`, and `--database /path/to/index`.
The standalone CLI uses the user's cache directory by default.
