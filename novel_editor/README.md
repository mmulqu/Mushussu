# Novel Diff Viewer

A lightweight, open-source web application for visualizing LLM edits to novel manuscripts. View line-by-line changes with color-coded diffs, browse commit history, and track how your novel evolves through AI-assisted editing.

## Features

- 📚 **File Browser**: Browse all novel files (.txt and .md) in your repository
- 🕐 **Commit History**: View chronological edit history with author and timestamps
- 🎨 **Color-Coded Diffs**:
  - Green lines = Added text
  - Red lines = Removed text
  - Gray lines = Unchanged context
- 🔍 **Unified Diff View**: See changes in a traditional diff format
- 📄 **File Content View**: Read current file contents
- 🔗 **Git Integration**: Works with your existing git repository
- ⚡ **Lightweight**: No build process, just HTML/CSS/JS frontend

## Prerequisites

- Python 3.8+
- Git repository with your novel files
- Modern web browser

## Installation

1. Install Python dependencies:
```bash
cd /home/user/Mushussu/novel_editor
pip install -r requirements.txt
```

## Usage

### Start the Server

```bash
python server.py
```

The server will start on `http://localhost:5000`

### Custom Repository Path

By default, the server looks for files in `/home/user/Mushussu/Novel_original/`. To use a different repository:

```bash
export REPO_PATH=/path/to/your/novel/repo
python server.py
```

### Using the Interface

1. **Browse Files**: Click on any file in the left sidebar to select it
2. **View Commits**: Recent commits appear in the commit history panel
3. **See Changes**: Click on a commit to view the diff with color-coded changes
4. **Filter Commits**: Check "Filter by selected file" to see only commits affecting the current file
5. **Switch Views**: Use the top buttons to toggle between:
   - Unified Diff (default)
   - Split View (coming soon)
   - File Content

## Architecture

### Backend (Flask)
- `server.py`: REST API for git operations
- Endpoints:
  - `/api/files` - List all novel files
  - `/api/file/<path>` - Get file content
  - `/api/commits` - Get commit history
  - `/api/diff/<hash>` - Get commit diff
  - `/api/file/history/<path>` - Get file change history

### Frontend (Vanilla JS)
- `static/index.html` - Main HTML structure
- `static/styles.css` - Dark theme styling
- `static/app.js` - Application logic and diff parsing

## API Usage

The backend provides a REST API that can be used by LLM agents or other tools:

### List Files
```bash
curl http://localhost:5000/api/files
```

### Get File Content
```bash
curl http://localhost:5000/api/file/Novel_original/Chapter1.txt
```

### Get Commit History
```bash
curl http://localhost:5000/api/commits?limit=20
```

### Get Commit Diff
```bash
curl http://localhost:5000/api/diff/<commit-hash>
```

### Get File History
```bash
curl http://localhost:5000/api/file/history/Novel_original/Chapter1.txt
```

## LLM Agent Integration

This tool is designed to work seamlessly with the Claude Agent SDK. Your LLM agent can:

1. **Make edits** to novel files using standard file operations
2. **Commit changes** using git commands
3. **Visualize edits** through this web interface

Example workflow:
```bash
# LLM makes edits
echo "new content" >> Novel_original/Chapter1.txt

# LLM commits changes
git add Novel_original/Chapter1.txt
git commit -m "Add new scene to Chapter 1"

# View changes in the diff viewer at http://localhost:5000
```

## Customization

### Change Novel Directory

Edit `server.py` line 16:
```python
NOVEL_DIR = 'Novel_original'  # Change this to your directory
```

### Adjust File Types

Edit `server.py` line 39 to include additional file types:
```python
if file_path.suffix in ['.txt', '.md', '.rst', '.adoc']:
```

### Theme Customization

Edit `static/styles.css` to change colors. Variables are defined at the top:
```css
:root {
    --bg-primary: #1e1e1e;
    --accent-color: #007acc;
    --add-color: #4ec9b0;
    --remove-color: #f48771;
}
```

## Troubleshooting

### Server won't start
- Check if port 5000 is already in use
- Verify Python dependencies are installed: `pip install -r requirements.txt`

### No files appear
- Verify `NOVEL_DIR` matches your directory structure
- Check that files have `.txt` or `.md` extensions
- Ensure the repository path is correct

### Diffs not showing
- Verify git repository has commits
- Check that files were committed to git
- Ensure commit affected `.txt` or `.md` files

## License

Open source - feel free to modify and distribute.

## Future Enhancements

- Split view diff mode
- Side-by-side file comparison
- Export diff reports
- Search functionality
- Diff statistics (lines added/removed)
- Support for more file formats
- Real-time updates via websockets

## Credits

Built for novel writers using LLM assistance to track and visualize editorial changes.
