# EnderTrack — Community Plugins

Community plugins for [EnderTrack — imaging](https://github.com/Hugo-LE-GUENNO/EnderTrack/tree/imaging).

## Structure

```
plugins-python/       ← Single-file Python plugins
  catalog.json        ← Plugin index
  my-plugin/
    my-plugin.py

plugins-advanced/     ← Multi-file JS/Python plugins
  catalog.json        ← Plugin index
  my-plugin/
    plugin.json       ← Manifest (required)
    bridge.js
    ui.js
    ui.css
```

## Submit a plugin

👉 [How to contribute a Python plugin](https://github.com/Hugo-LE-GUENNO/EnderTrack/blob/imaging/docs/community-plugins.md)  
👉 [Python plugin API reference](https://github.com/Hugo-LE-GUENNO/EnderTrack/blob/imaging/docs/python-plugins.md)

Open a Pull Request with your plugin folder in the right directory.

### Python plugin — `catalog.json` entry

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
