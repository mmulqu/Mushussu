// Novel Editor - Simplified GitHub Editor with Diff View

const GITHUB_API = 'https://api.github.com';
const CONFIG_KEY = 'novel-editor-config';

// State
const state = {
    owner: null,
    repo: null,
    branch: 'main',
    path: '',
    token: null,
    authorName: 'Novel Author',
    authorEmail: 'author@example.com',

    files: [],
    currentFile: null,
    originalContent: '',
    currentContent: '',
    fileSha: null,
    hasChanges: false,
    isMarkdown: false,
    isViewingCommitDiff: false  // Track if viewing a commit diff vs live editing
};

// DOM Elements
const el = {
    settingsModal: document.getElementById('settings-modal'),
    settingsBtn: document.getElementById('settings-btn'),
    closeSettings: document.getElementById('close-settings'),
    saveSettings: document.getElementById('save-settings'),

    repoInput: document.getElementById('repo-input'),
    branchInput: document.getElementById('branch-input'),
    pathInput: document.getElementById('path-input'),
    tokenInput: document.getElementById('token-input'),
    authorName: document.getElementById('author-name'),
    authorEmail: document.getElementById('author-email'),

    fileSelect: document.getElementById('file-select'),
    refreshBtn: document.getElementById('refresh-btn'),
    saveBtn: document.getElementById('save-btn'),

    editor: document.getElementById('editor'),
    wordCount: document.getElementById('word-count'),
    changeIndicator: document.getElementById('change-indicator'),
    diffView: document.getElementById('diff-view'),
    syncScroll: document.getElementById('sync-scroll'),

    toggleCommits: document.getElementById('toggle-commits'),
    commitsPanel: document.getElementById('commits-panel'),
    closeCommits: document.getElementById('close-commits'),
    commitsList: document.getElementById('commits-list'),

    collapseDiff: document.getElementById('collapse-diff'),
    expandDiff: document.getElementById('expand-diff'),

    statusMessage: document.getElementById('status-message'),
    fileInfo: document.getElementById('file-info')
};

// Initialize
async function init() {
    setupEventListeners();
    loadConfig();

    // Show settings if not configured
    if (!state.owner || !state.repo) {
        el.settingsModal.style.display = 'flex';
    } else {
        await loadFiles();
    }
}

function setupEventListeners() {
    // Settings
    el.settingsBtn.addEventListener('click', () => el.settingsModal.style.display = 'flex');
    el.closeSettings.addEventListener('click', () => el.settingsModal.style.display = 'none');
    el.saveSettings.addEventListener('click', handleSaveSettings);

    // File operations
    el.fileSelect.addEventListener('change', handleFileSelect);
    el.refreshBtn.addEventListener('click', handleRefresh);
    el.saveBtn.addEventListener('click', handleSave);

    // Editor
    el.editor.addEventListener('input', handleEditorChange);
    el.editor.addEventListener('scroll', handleEditorScroll);

    // Diff view scroll (for bidirectional sync)
    el.diffView.addEventListener('scroll', handleDiffScroll);

    // Commits
    el.toggleCommits.addEventListener('click', () => {
        el.commitsPanel.style.display = 'flex';
        loadCommits();
    });
    el.closeCommits.addEventListener('click', () => el.commitsPanel.style.display = 'none');

    // Collapse/expand diff pane
    el.collapseDiff.addEventListener('click', () => {
        const diffPane = document.querySelector('.diff-pane');
        const mainContent = document.querySelector('.main-content');
        diffPane.style.display = 'none';
        mainContent.style.gridTemplateColumns = '1fr';
        el.expandDiff.style.display = 'inline-block';
    });

    el.expandDiff.addEventListener('click', () => {
        const diffPane = document.querySelector('.diff-pane');
        const mainContent = document.querySelector('.main-content');
        diffPane.style.display = 'flex';
        mainContent.style.gridTemplateColumns = '1fr 1fr';
        el.expandDiff.style.display = 'none';
    });
}

// Scroll sync (bidirectional)
let isScrolling = false;

function handleEditorScroll() {
    // Disable scroll sync when viewing a commit diff (content doesn't match editor)
    if (!el.syncScroll.checked || isScrolling || state.isViewingCommitDiff) return;

    isScrolling = true;
    const editorHeight = el.editor.scrollHeight - el.editor.clientHeight;
    const diffHeight = el.diffView.scrollHeight - el.diffView.clientHeight;

    if (editorHeight > 0 && diffHeight > 0) {
        const scrollPercentage = el.editor.scrollTop / editorHeight;
        el.diffView.scrollTop = scrollPercentage * diffHeight;
    }

    setTimeout(() => isScrolling = false, 50);
}

function handleDiffScroll() {
    // Disable scroll sync when viewing a commit diff (content doesn't match editor)
    if (!el.syncScroll.checked || isScrolling || state.isViewingCommitDiff) return;

    isScrolling = true;
    const editorHeight = el.editor.scrollHeight - el.editor.clientHeight;
    const diffHeight = el.diffView.scrollHeight - el.diffView.clientHeight;

    if (editorHeight > 0 && diffHeight > 0) {
        const scrollPercentage = el.diffView.scrollTop / diffHeight;
        el.editor.scrollTop = scrollPercentage * editorHeight;
    }

    setTimeout(() => isScrolling = false, 50);
}

function loadConfig() {
    try {
        const saved = localStorage.getItem(CONFIG_KEY);
        if (saved) {
            const config = JSON.parse(saved);
            Object.assign(state, config);

            el.repoInput.value = `${state.owner}/${state.repo}`;
            el.branchInput.value = state.branch;
            el.pathInput.value = state.path;
            el.tokenInput.value = state.token || '';
            el.authorName.value = state.authorName;
            el.authorEmail.value = state.authorEmail;
        }
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

function saveConfig() {
    try {
        localStorage.setItem(CONFIG_KEY, JSON.stringify({
            owner: state.owner,
            repo: state.repo,
            branch: state.branch,
            path: state.path,
            token: state.token,
            authorName: state.authorName,
            authorEmail: state.authorEmail
        }));
    } catch (error) {
        console.error('Error saving config:', error);
    }
}

async function handleSaveSettings() {
    try {
        const repoUrl = el.repoInput.value.trim();
        const match = repoUrl.match(/(?:github\.com\/)?([^\/]+)\/([^\/]+)/);

        if (!match) {
            throw new Error('Invalid repository format. Use: owner/repo');
        }

        state.owner = match[1];
        state.repo = match[2].replace(/\.git$/, '');
        state.branch = el.branchInput.value.trim() || 'main';
        state.path = el.pathInput.value.trim();
        state.token = el.tokenInput.value.trim();
        state.authorName = el.authorName.value.trim();
        state.authorEmail = el.authorEmail.value.trim();

        saveConfig();
        el.settingsModal.style.display = 'none';

        await loadFiles();
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

// GitHub API
async function githubApi(endpoint, options = {}) {
    const headers = {
        'Accept': 'application/vnd.github.v3+json',
        ...options.headers
    };

    if (state.token) {
        headers['Authorization'] = `token ${state.token}`;
    }

    const response = await fetch(`${GITHUB_API}${endpoint}`, {
        ...options,
        headers
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.message || `GitHub API error: ${response.status}`);
    }

    return response.json();
}

async function loadFiles() {
    try {
        showStatus('Loading files...');

        const data = await githubApi(`/repos/${state.owner}/${state.repo}/git/trees/${state.branch}?recursive=1`);

        state.files = data.tree
            .filter(item => {
                if (item.type !== 'blob') return false;
                const isTextFile = /\.(txt|md)$/i.test(item.path);
                if (state.path) {
                    return isTextFile && item.path.startsWith(state.path);
                }
                return isTextFile;
            })
            .map(item => ({
                name: item.path.split('/').pop(),
                path: item.path,
                sha: item.sha
            }))
            .sort((a, b) => a.name.localeCompare(b.name));

        // Populate file select
        el.fileSelect.innerHTML = '<option value="">Select a file...</option>';
        state.files.forEach(file => {
            const option = document.createElement('option');
            option.value = file.path;
            option.textContent = file.name;
            el.fileSelect.appendChild(option);
        });

        showStatus(`Loaded ${state.files.length} files`);

    } catch (error) {
        showStatus(`Error loading files: ${error.message}`, 'error');
    }
}

async function handleFileSelect() {
    const filePath = el.fileSelect.value;
    if (!filePath) return;

    // Return to live editing mode (re-enable scroll sync)
    state.isViewingCommitDiff = false;

    try {
        showStatus('Loading file...');

        const data = await githubApi(`/repos/${state.owner}/${state.repo}/contents/${filePath}?ref=${state.branch}`);

        state.currentFile = filePath;
        state.fileSha = data.sha;
        state.originalContent = atob(data.content);
        state.currentContent = state.originalContent;
        state.isMarkdown = filePath.endsWith('.md');

        el.editor.value = state.originalContent;
        el.editor.placeholder = '';

        updateWordCount();
        updateDiff();

        el.fileInfo.textContent = filePath;
        showStatus('File loaded');

    } catch (error) {
        showStatus(`Error loading file: ${error.message}`, 'error');
    }
}

async function handleRefresh() {
    if (!state.currentFile) return;

    const currentFile = state.currentFile;
    el.fileSelect.value = '';
    await loadFiles();

    // Reselect current file
    el.fileSelect.value = currentFile;
    await handleFileSelect();
}

async function handleSave() {
    if (!state.currentFile || !state.hasChanges) return;
    if (!state.token) {
        showStatus('GitHub token required for push. Check settings.', 'error');
        return;
    }

    const message = prompt('Commit message:', 'Update ' + state.currentFile.split('/').pop());
    if (!message) return;

    try {
        el.saveBtn.disabled = true;
        showStatus('Committing...');

        // Update file content
        await githubApi(`/repos/${state.owner}/${state.repo}/contents/${state.currentFile}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                content: btoa(unescape(encodeURIComponent(state.currentContent))),
                sha: state.fileSha,
                branch: state.branch,
                committer: {
                    name: state.authorName,
                    email: state.authorEmail
                },
                author: {
                    name: state.authorName,
                    email: state.authorEmail
                }
            })
        });

        // Update state
        state.originalContent = state.currentContent;
        state.hasChanges = false;
        updateDiff();

        showStatus('✓ Committed and pushed!', 'success');

        // Refresh to get new SHA
        setTimeout(() => handleRefresh(), 1000);

    } catch (error) {
        showStatus(`Error saving: ${error.message}`, 'error');
    } finally {
        el.saveBtn.disabled = false;
    }
}

function handleEditorChange() {
    state.currentContent = el.editor.value;
    state.hasChanges = state.currentContent !== state.originalContent;

    // Return to live editing mode when user makes changes (re-enable scroll sync)
    state.isViewingCommitDiff = false;

    el.saveBtn.disabled = !state.hasChanges;
    el.changeIndicator.textContent = state.hasChanges ? '● Modified' : '';

    updateWordCount();
    updateDiff();
}

function updateWordCount() {
    const words = el.editor.value.trim().split(/\s+/).filter(w => w.length > 0).length;
    el.wordCount.textContent = `${words} word${words !== 1 ? 's' : ''}`;
}

function updateDiff() {
    if (!state.currentFile) {
        el.diffView.innerHTML = '<div class="empty-state"><p>No file selected</p></div>';
        return;
    }

    if (!state.hasChanges) {
        el.diffView.innerHTML = '<div class="empty-state"><p>No changes</p><small>Edit the text to see differences</small></div>';
        return;
    }

    const diff = computeDiff(state.originalContent, state.currentContent);
    renderDiff(diff);
}

function computeDiff(oldText, newText) {
    const oldLines = oldText.split('\n');
    const newLines = newText.split('\n');

    // Simple line-by-line diff using LCS approach
    const diff = [];
    let i = 0, j = 0;

    while (i < oldLines.length || j < newLines.length) {
        if (i >= oldLines.length) {
            // Remaining new lines
            diff.push({ type: 'add', content: newLines[j] });
            j++;
        } else if (j >= newLines.length) {
            // Remaining old lines
            diff.push({ type: 'remove', content: oldLines[i] });
            i++;
        } else if (oldLines[i] === newLines[j]) {
            // Same line
            diff.push({ type: 'context', content: oldLines[i] });
            i++;
            j++;
        } else {
            // Different lines - check if it's a replacement or add/remove
            const nextOldMatch = newLines.indexOf(oldLines[i], j);
            const nextNewMatch = oldLines.indexOf(newLines[j], i);

            if (nextNewMatch !== -1 && (nextOldMatch === -1 || nextNewMatch < nextOldMatch)) {
                // Line was removed
                diff.push({ type: 'remove', content: oldLines[i] });
                i++;
            } else {
                // Line was added
                diff.push({ type: 'add', content: newLines[j] });
                j++;
            }
        }
    }

    return diff;
}

function renderDiff(diff) {
    el.diffView.innerHTML = '';

    let contextCount = 0;
    const maxContext = 3;

    diff.forEach((line, index) => {
        // Skip excessive context
        if (line.type === 'context') {
            contextCount++;

            // Show only first/last few context lines around changes
            const hasChangeBefore = index > 0 && diff[index - 1].type !== 'context';
            const hasChangeAfter = index < diff.length - 1 && diff[index + 1].type !== 'context';

            if (!hasChangeBefore && !hasChangeAfter && contextCount > maxContext) {
                // Skip this context line if we're far from changes
                if (contextCount === maxContext + 1) {
                    const skipLine = document.createElement('div');
                    skipLine.className = 'diff-line context';
                    skipLine.innerHTML = '<span class="line-prefix">⋮</span><span class="line-content">...</span>';
                    el.diffView.appendChild(skipLine);
                }
                return;
            }
        } else {
            contextCount = 0;
        }

        const lineDiv = document.createElement('div');
        lineDiv.className = `diff-line ${line.type}`;

        const prefix = document.createElement('span');
        prefix.className = 'line-prefix';
        prefix.textContent = line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' ';

        const content = document.createElement('span');
        content.className = 'line-content';

        // Render markdown for .md files
        if (state.isMarkdown && typeof marked !== 'undefined' && line.content.trim()) {
            try {
                content.innerHTML = marked.parseInline(line.content);
            } catch (e) {
                content.textContent = line.content || ' ';
            }
        } else {
            content.textContent = line.content || ' ';
        }

        lineDiv.appendChild(prefix);
        lineDiv.appendChild(content);
        el.diffView.appendChild(lineDiv);
    });
}

async function loadCommits() {
    try {
        el.commitsList.innerHTML = '<div class="loading">Loading commits...</div>';

        let endpoint = `/repos/${state.owner}/${state.repo}/commits?per_page=20&sha=${state.branch}`;
        if (state.currentFile) {
            endpoint += `&path=${state.currentFile}`;
        }

        const commits = await githubApi(endpoint);

        el.commitsList.innerHTML = '';

        commits.forEach(commit => {
            const item = document.createElement('div');
            item.className = 'commit-item';

            const hash = document.createElement('div');
            hash.className = 'commit-hash';
            hash.textContent = commit.sha.substring(0, 7);

            const message = document.createElement('div');
            message.className = 'commit-message';
            message.textContent = commit.commit.message.split('\n')[0];

            const meta = document.createElement('div');
            meta.className = 'commit-meta';
            const date = new Date(commit.commit.author.date);
            meta.textContent = `${commit.commit.author.name} • ${formatDate(date)}`;

            item.appendChild(hash);
            item.appendChild(message);
            item.appendChild(meta);

            item.addEventListener('click', () => viewCommitDiff(commit.sha));

            el.commitsList.appendChild(item);
        });

    } catch (error) {
        el.commitsList.innerHTML = `<div class="loading">Error loading commits: ${error.message}</div>`;
    }
}

async function viewCommitDiff(sha) {
    try {
        // Close commits panel so diff is fully visible and scrollable
        el.commitsPanel.style.display = 'none';

        // Mark that we're viewing a commit diff (disables scroll sync)
        state.isViewingCommitDiff = true;

        showStatus('Loading commit diff...');

        const response = await fetch(`${GITHUB_API}/repos/${state.owner}/${state.repo}/commits/${sha}`, {
            headers: {
                'Accept': 'application/vnd.github.v3.diff',
                ...(state.token ? { 'Authorization': `token ${state.token}` } : {})
            }
        });

        const diffText = await response.text();

        // Parse and render the diff with proper styling
        el.diffView.innerHTML = '';

        const lines = diffText.split('\n');
        lines.forEach(line => {
            const lineDiv = document.createElement('div');
            lineDiv.className = 'diff-line';

            const prefix = document.createElement('span');
            prefix.className = 'line-prefix';

            const content = document.createElement('span');
            content.className = 'line-content';

            if (line.startsWith('+') && !line.startsWith('+++')) {
                lineDiv.classList.add('add');
                prefix.textContent = '+';
                content.textContent = line.substring(1);
            } else if (line.startsWith('-') && !line.startsWith('---')) {
                lineDiv.classList.add('remove');
                prefix.textContent = '-';
                content.textContent = line.substring(1);
            } else if (line.startsWith('@@')) {
                lineDiv.classList.add('context');
                prefix.textContent = '@';
                content.textContent = line;
                content.style.color = 'var(--accent-color)';
            } else {
                lineDiv.classList.add('context');
                prefix.textContent = ' ';
                content.textContent = line;
            }

            lineDiv.appendChild(prefix);
            lineDiv.appendChild(content);
            el.diffView.appendChild(lineDiv);
        });

        showStatus('Showing commit ' + sha.substring(0, 7));

    } catch (error) {
        showStatus(`Error loading commit: ${error.message}`, 'error');
    }
}

function showStatus(message, type = '') {
    el.statusMessage.textContent = message;
    el.statusMessage.parentElement.className = `status-bar ${type}`;
}

function formatDate(date) {
    const now = new Date();
    const diff = now - date;

    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}m ago`;
    }
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}h ago`;
    }
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
    }

    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Start the app
init();
