if vim.g.loaded_django_docs then return end
vim.g.loaded_django_docs = true
vim.api.nvim_create_user_command('DjangoDocs', function(opts)
  require('django_docs').search(opts.args)
end, { nargs = '*', force = true, desc = 'Search offline Django documentation' })
vim.api.nvim_create_user_command('DjangoDocsIndex', function()
  require('django_docs').index()
end, { desc = 'Rebuild offline Django documentation index' })
