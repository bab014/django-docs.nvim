local M = {}
local base = vim.fn.fnamemodify(debug.getinfo(1, 'S').source:sub(2), ':p:h:h:h')
local config = { python = 'python3', limit = 10 }
local busy = false

function M.setup(opts)
  config = vim.tbl_extend('force', { python = 'python3', limit = 10 }, opts or {})
end

local function run(extra, callback)
  if not vim.system then
    vim.notify('django-docs.nvim requires Neovim 0.10+', vim.log.levels.ERROR)
    return
  end
  if not config.docs_path or config.docs_path == '' then
    vim.notify('Set docs_path in require("django_docs").setup({ docs_path = "..." })', vim.log.levels.ERROR)
    return
  end
  if busy then
    vim.notify('Django documentation search is still running')
    return
  end
  local root = vim.fn.fnamemodify(vim.fn.expand(config.docs_path), ':p'):gsub('/$', '')
  local database = vim.fn.stdpath('cache') .. '/django-docs.nvim/' .. vim.fn.sha256(root):sub(1, 16) .. '.sqlite3'
  local command = { config.python, base .. '/python/search.py', '--docs', root,
    '--database', database, '--limit', tostring(config.limit) }
  vim.list_extend(command, extra)
  busy = true
  local ok, err = pcall(vim.system, command, { text = true }, function(output)
    vim.schedule(function()
      busy = false
      if output.code ~= 0 then
        vim.notify(output.stderr ~= '' and output.stderr or output.stdout, vim.log.levels.ERROR)
        return
      end
      callback(output.stdout)
    end)
  end)
  if not ok then
    busy = false
    vim.notify(tostring(err), vim.log.levels.ERROR)
  end
end

function M.search(query)
  if not query or query == '' then
    vim.ui.input({ prompt = 'Search Django docs: ' }, function(input)
      if input and input ~= '' then M.search(input) end
    end)
    return
  end
  run({ '--json', query }, function(output)
    local ok, results = pcall(vim.json.decode, output)
    if not ok then
      vim.notify('Could not decode Django documentation results', vim.log.levels.ERROR)
      return
    end
    if #results == 0 then
      vim.notify('No matching Django documentation sections')
      return
    end
    vim.ui.select(results, {
      prompt = 'Django documentation: ' .. query,
      format_item = function(item)
        return item.title .. ' — ' .. vim.fn.fnamemodify(item.path, ':t') .. ':' .. item.line
      end,
    }, function(item)
      if item then
        vim.cmd('edit ' .. vim.fn.fnameescape(item.path))
        vim.api.nvim_win_set_cursor(0, { item.line, 0 })
        vim.cmd('normal! zz')
      end
    end)
  end)
end

function M.index()
  run({ '--index' }, function(output) vim.notify(vim.trim(output)) end)
end

return M
