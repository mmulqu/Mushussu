# 📖 Novel Diff Viewer

A lightweight, open-source web application for visualizing LLM edits to novel manuscripts. Perfect for tracking changes made by AI agents like Claude.

**[🚀 Live Demo](https://mmulqu.github.io/Mushussu/)** (GitHub Pages version)

![Novel Diff Viewer Screenshot](https://via.placeholder.com/800x450/0d1117/58a6ff?text=Novel+Diff+Viewer)

## ✨ Features

- **🎨 Color-Coded Diffs**: Green for additions, red for removals
- **📁 File Browser**: Browse all text and markdown files
- **📝 Commit History**: Chronological view of all changes
- **🔍 Filter by File**: See commit history for specific files
- **🌐 Pure Client-Side**: No server required, runs entirely in browser
- **🔓 Open Source**: MIT licensed, fork and customize as needed
- **🎯 GitHub Integration**: Works with any public GitHub repository

## 🚀 Quick Start

### Option 1: Use the Hosted Version (Easiest)

1. Visit: **https://mmulqu.github.io/Mushussu/**
2. Enter your GitHub repository URL (e.g., `username/repo`)
3. Optionally specify a directory path (e.g., `Novel_original`)
4. Click "Connect Repository"

### Option 2: Fork for Your Own Repo

1. **Fork this repository** on GitHub
2. **Enable GitHub Pages**:
   - Go to Settings → Pages
   - Source: Deploy from branch `main`
   - Folder: `/docs`
3. **Visit your GitHub Pages URL**: `https://yourusername.github.io/yourrepo/`

### Option 3: Run Locally

```bash
# Clone the repository
git clone https://github.com/mmulqu/Mushussu.git
cd Mushussu/docs

# Serve with any static file server
python3 -m http.server 8000
# OR
npx serve .

# Open browser to http://localhost:8000
```

## 📚 Usage

### For Public Repositories

Just enter the repository URL - no authentication needed!

```
mmulqu/Mushussu
```

### For Private Repositories

1. **Create a GitHub Personal Access Token**:
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Scopes: Select `repo` (Full control of private repositories)
   - Click "Generate token" and copy it

2. **Enter the token** in the "GitHub Token" field when connecting

### Filter by Directory

If your novel files are in a specific directory (e.g., `Novel_original`), enter that path to filter the view:

```
Novel Directory: Novel_original
```

## 🤖 Integration with Claude Agent SDK

This tool is designed to work seamlessly with Claude Agent SDK workflows:

1. **Claude edits your novel files** via the SDK
2. **Claude commits the changes** to git
3. **Visualize the edits** in the Novel Diff Viewer

Example workflow:
```bash
# Claude Agent SDK session
claude> Edit Chapter1.txt and add a new dialogue scene
# ... Claude makes edits ...
claude> Commit the changes
# ... Claude commits to git ...

# Then view the changes at:
# https://mmulqu.github.io/Mushussu/
```

## 🛠️ How It Works

### Architecture

```
┌─────────────────┐
│   Web Browser   │
│  (HTML/CSS/JS)  │
└────────┬────────┘
         │
         │ HTTPS Requests
         ▼
┌─────────────────┐
│  GitHub API     │
│  - Commits      │
│  - File Tree    │
│  - Diffs        │
│  - Contents     │
└─────────────────┘
```

### No Backend Required

This is a **pure client-side application**:
- Uses GitHub API directly from the browser
- No server, no database, no installation
- State saved in browser localStorage
- Works with any GitHub repository

### Rate Limits

**Without token**: 60 requests/hour per IP
**With token**: 5,000 requests/hour

For most novel writing workflows, the free tier is sufficient. Add a token if you hit rate limits.

## 📂 Project Structure

```
docs/
├── index.html      # Main application HTML
├── styles.css      # GitHub-themed dark mode styles
├── app.js          # GitHub API integration & diff rendering
└── README.md       # This file
```

## 🎨 Features in Detail

### Diff Visualization

- **Line-by-line comparison** with color coding
- **Line numbers** for easy reference
- **Unified diff format** (standard git diff)
- **Monospace font** for prose readability

### File Browser

- Lists all `.txt` and `.md` files
- Optional directory filtering
- File size display
- Sorted alphabetically

### Commit History

- Chronological commit list
- Commit hash, message, author
- Relative timestamps (e.g., "2h ago")
- Filter by selected file

## 🔒 Privacy & Security

- **No data stored on servers**: Everything runs in your browser
- **GitHub tokens never leave your machine**: Stored in localStorage only
- **Open source**: Audit the code yourself
- **No tracking or analytics**: Pure static site

## 🤝 For Other Users

### How to Use This Tool

**Anyone can use the hosted version** without forking:
1. Visit https://mmulqu.github.io/Mushussu/
2. Enter your GitHub repository URL
3. Start exploring your diffs

**Or fork it for customization**:
1. Fork the repository
2. Customize the theme, filters, or features
3. Enable GitHub Pages on your fork
4. Share your customized version

### Use Cases

- **Novel writing with AI assistance**: Track Claude's edits
- **Collaborative writing**: Review co-author changes
- **Version control visualization**: Better than raw git diffs for prose
- **Manuscript history**: See how your story evolved
- **Educational**: Learn how diffs work

## 🛣️ Roadmap

Future enhancements:
- [ ] Side-by-side diff view
- [ ] Export diffs as formatted documents
- [ ] Compare arbitrary commits
- [ ] Syntax highlighting for code files
- [ ] Dark/light theme toggle
- [ ] Mobile-responsive improvements

## 📝 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built for use with:
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
- [GitHub REST API](https://docs.github.com/en/rest)

## 🐛 Issues & Contributing

Found a bug? Have a feature request?

- **Issues**: https://github.com/mmulqu/Mushussu/issues
- **Pull Requests**: Welcome!

## 📞 Support

- GitHub Issues: Best for bugs and features
- Documentation: This README
- Examples: See the live demo with the Mushussu repo

---

**Made with 📚 for novel writers using AI assistance**
