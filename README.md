# EnderTrack — Community Plugins

Community plugins for [EnderTrack](https://github.com/Hugo-LE-GUENNO/EnderTrack).

## Structure

```
plugins-python/       ← Single-file Python plugins
  catalog.json        ← Plugin index
  my-plugin/
    my-plugin.py
    data/             ← Optional assets

plugins-advanced/     ← Multi-file JS/Python plugins
  catalog.json        ← Plugin index
  my-plugin/
    plugin.json       ← Manifest (required)
    bridge.js
    ui.js
    ui.css
```

## Submit a plugin

Open a Pull Request with your plugin folder in the right directory.

### Python plugin — `plugin.json` entry

```json
{
  "id": "my-plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "What it does",
  "author": "Your Name",
  "folder": "my-plugin",
  "main": "my-plugin.py"
}
```

### Advanced plugin — `plugin.json` manifest

```json
{
  "id": "myPlugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "What it does",
  "icon": "🔌",
  "tools": [],
  "widgets": [],
  "navButtons": []
}
```

## License

GPLv3
