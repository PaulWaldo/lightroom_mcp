# Lua Tests

This directory is reserved for unit tests of the Lightroom Classic plugin code
in `lightroom-python-bridge.lrdevplugin/`.

## Test Framework

Lua unit tests use **[busted](https://lunarmodules.github.io/busted/)**, the
standard Lua BDD testing framework.

Install via LuaRocks:

```bash
luarocks install busted
```

## Running Tests

```bash
# Run all Lua tests from the repo root
busted tests/lua/

# Run a single file
busted tests/lua/test_CommandRouter.lua

# With verbose output
busted --verbose tests/lua/
```

## Planned Test Files

| File | Module under test | Priority |
|------|------------------|----------|
| `test_MessageProtocol.lua` | `MessageProtocol.lua` — JSON encoding, backslash escaping | High |
| `test_CommandRouter.lua` | `CommandRouter.lua` — handler dispatch, unknown command | High |
| `test_ErrorUtils.lua` | `ErrorUtils.lua` — `createError` shape, severity defaults | Medium |
| `test_CatalogModule.lua` | `CatalogModule.lua` — parameter validation stubs | Medium |

## Mocking Strategy

The Lightroom SDK (`LrCatalog`, `LrPhoto`, `LrDevelopController`, etc.) is not
available outside Lightroom.  Tests should define minimal stub tables at the top
of each test file:

```lua
-- stub LrPathUtils used by MessageProtocol
LrPathUtils = { child = function(a, b) return a .. "/" .. b end }
```

Keep stubs minimal — only implement the methods your test actually exercises.
