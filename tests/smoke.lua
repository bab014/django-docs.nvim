-- Run from the Markdown root:
-- nvim --headless -i NONE -u NONE -l docsearch/django-docs.nvim/tests/smoke.lua
local root = vim.fn.getcwd()
local package = root .. '/docsearch/django-docs.nvim'
vim.opt.runtimepath:prepend(package)
vim.cmd('runtime plugin/django_docs.lua')
local done, failure = false, nil
local messages = {}
vim.notify = function(message, level)
  table.insert(messages, message)
  if level == vim.log.levels.ERROR then failure = message; done = true end
end
require('django_docs').setup({ docs_path = root })
assert(vim.fn.exists(':DjangoDocs') == 2)
assert(vim.fn.exists(':DjangoDocsIndex') == 2)
vim.ui.select = function(results, opts, callback)
  assert(results[1].title:find('Creating models', 1, true), vim.inspect(results))
  callback(results[1])
  assert(vim.api.nvim_buf_get_name(0) == root .. '/intro/tutorial02.md')
  assert(vim.api.nvim_get_current_line() == '## Creating models')
  done = true
end
vim.cmd('DjangoDocs how to build a model')
assert(vim.wait(30000, function() return done end, 20), 'Search timed out')
assert(not failure, failure)
local count = #messages
vim.cmd('DjangoDocsIndex')
assert(vim.wait(30000, function() return #messages > count end, 20), 'Index rebuild timed out')
assert(not failure, failure)
assert(messages[#messages]:find('Indexed', 1, true))
print('Verified plugin commands, async search, result selection, source line, and index rebuild.')
vim.cmd('qa!')
