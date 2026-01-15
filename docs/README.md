# 📝 Novel Editor

A simple web-based text editor for novel writing with real-time diff visualization. Perfect for tracking changes made by LLM agents like Claude or your own edits.

**[🚀 Try it now](https://mmulqu.github.io/Mushussu/)** - No installation required!

## ✨ What It Does

1. **Edit your novel files** in a clean text editor
2. **See changes in real-time** - green for additions, red for removals
3. **Commit & push** directly to GitHub
4. **View commit history** to see what changed when

That's it. Simple and focused.

## 🚀 Quick Start

### 1. Get a GitHub Token

You need a token to read/write your repository:

1. Go to: https://github.com/settings/tokens/new?scopes=repo
2. Give it a name like "Novel Editor"
3. Select scope: **`repo`** (Full control of private repositories)
4. Click "Generate token"
5. **Copy the token** (you won't see it again!)

### 2. Open the Editor

Visit: **https://mmulqu.github.io/Mushussu/**

### 3. Configure Settings

Click the ⚙️ Settings button and enter:

- **Repository**: `your-username/your-repo` (e.g., `mmulqu/Mushussu`)
- **Branch**: `main` (or whatever branch you use)
- **Novel Directory**: `Novel_original` (or your folder path)
- **GitHub Token**: Paste the token you created
- **Author Name/Email**: Your name for commits

Click "Save & Load Files"

### 4. Start Writing!

1. Select a file from the dropdown
2. Edit the text in the left pane
3. See your changes highlighted in the right pane
4. Click "Commit & Push" when ready

## 📖 Usage

### Editing

- Type in the **left pane** (the editor)
- See **real-time diffs** in the right pane
- **Green** = added lines
- **Red** = removed lines
- **Gray** = unchanged context

### Saving

1. Make your edits
2. Click **"Commit & Push"**
3. Enter a commit message
4. Done! Your changes are on GitHub

### Viewing History

- Click **"Recent Commits"** to see commit history
- Click any commit to view its diff
- Filter commits to current file automatically

### Refreshing

- Click **"Refresh"** to reload from GitHub
- Useful after your LLM agent makes changes
- Also refreshes automatically after you commit

## 🤖 Works With LLM Agents

This editor is designed to work alongside Claude Agent SDK:

**Typical Workflow:**

1. **Claude edits files** via the Agent SDK
2. **Claude commits** to GitHub
3. **Click "Refresh"** in the editor to see Claude's changes
4. **Make your own edits** in the web editor
5. **Commit your changes** back

Both you and the AI can edit the same files, and you'll see all changes highlighted!

## 🎨 Interface

```
┌─────────────────────────────────────────────────────────┐
│  📝 Novel Editor         [Chapter1.txt ▼] [Refresh] [Commit] [⚙️]
├──────────────────────────┬──────────────────────────────┤
│  ✏️ Editor              │  🔍 Changes                  │
│                          │                              │
│  Your text goes here...  │  + Added line (green)        │
│  Edit freely!            │  - Removed line (red)        │
│                          │    Unchanged line            │
│                          │                              │
│  (word count)            │  [Recent Commits]            │
└──────────────────────────┴──────────────────────────────┘
│  Ready                                    Chapter1.txt   │
└─────────────────────────────────────────────────────────┘
```

## 🔒 Security & Privacy

- **Token stays local**: Stored in your browser's localStorage only
- **No backend**: Direct GitHub API calls from your browser
- **Open source**: Audit the code yourself - it's just 3 files
- **No tracking**: Zero analytics or data collection

## 🛠️ Technical Details

**Tech Stack:**
- Pure vanilla JavaScript (no frameworks)
- GitHub REST API for all operations
- localStorage for config persistence
- CSS Grid for layout

**File Size:**
- HTML: ~5KB
- CSS: ~7KB
- JavaScript: ~13KB
- **Total: ~25KB** uncompressed

**No Build Process:**
- No npm, no webpack, no compilation
- Just open `index.html` in a browser
- Or serve with any static file server

## 📂 How to Host Your Own

### Option 1: GitHub Pages (Easiest)

1. Fork this repository
2. Enable GitHub Pages:
   - Settings → Pages
   - Source: `main` branch
   - Folder: `/docs`
3. Visit: `https://yourusername.github.io/yourrepo/`

### Option 2: Any Static Host

Upload the `docs/` folder to:
- Netlify
- Vercel
- Cloudflare Pages
- Any web server

### Option 3: Run Locally

```bash
cd docs
python3 -m http.server 8000
# Visit: http://localhost:8000
```

## 💡 Use Cases

- **Novel writing with AI assistance**: Track Claude's edits
- **Solo novel writing**: Simple editor + version control
- **Collaborative writing**: See what others changed
- **Manuscript revision**: Compare versions easily
- **Educational**: Learn how diffs work

## ❓ FAQ

**Q: Can I use this with private repos?**
A: Yes! Just make sure your GitHub token has `repo` scope.

**Q: Does it work offline?**
A: No, it needs GitHub API access to read/write files.

**Q: Can I edit multiple files at once?**
A: No, one file at a time. Switch files with the dropdown.

**Q: Will it work with other git hosts?**
A: No, it's GitHub-specific. But you could fork and adapt it!

**Q: What if I make changes and Claude makes changes?**
A: Click "Refresh" to load Claude's changes. If you have unsaved edits, you'll lose them. Commit often!

**Q: Can I see diffs between arbitrary commits?**
A: Not yet, but that's a good feature idea!

## 🐛 Issues & Contributing

Found a bug? Want a feature?

- **Issues**: https://github.com/mmulqu/Mushussu/issues
- **Pull Requests**: Welcome!
- **Discussions**: Use GitHub Discussions

## 📝 License

MIT License - Use it however you want!

## 🙏 Acknowledgments

Built for novel writers using AI tools like:
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
- [GitHub API](https://docs.github.com/en/rest)

---

**Made for writers who want to see what changed** 📚
