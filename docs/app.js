// Novel Diff Viewer - GitHub API Edition
// Pure client-side app for visualizing git diffs

const GITHUB_API = 'https://api.github.com';
const CACHE_KEY = 'novel-diff-viewer-config';

// Application state
const state = {
    owner: null,
    repo: null,
    basePath: '',
    token: null,
    files: [],
    commits: [],
    selectedFile: null,
    selectedCommit: null,
    viewMode: 'unified',
    filterByFile: false
};

// DOM Elements
const elements = {
    // Setup
    repoSetup: document.getElementById('repo-setup'),
    mainContent: document.getElementById('main-content'),
    repoUrlInput: document.getElementById('repo-url'),
    basePathInput: document.getElementById('base-path'),
    tokenInput: document.getElementById('github-token'),
    connectBtn: document.getElementById('connect-btn'),
    setupError: document.getElementById('setup-error'),
    changeRepoBtn: document.getElementById('change-repo-btn'),

    // Main UI
    currentRepoSpan: document.getElementById('current-repo'),
    fileList: document.getElementById('file-list'),
    commitList: document.getElementById('commit-list'),
    contentArea: document.getElementById('content-area'),
    currentFile: document.getElementById('current-file'),
    filterCheckbox: document.getElementById('filter-current-file'),
    btnUnified: document.getElementById('btn-unified'),
    btnFile: document.getElementById('btn-file')
};

// Initialize application
async function init() {
    setupEventListeners();
    loadConfig();
}

function setupEventListeners() {
    elements.connectBtn.addEventListener('click', handleConnect);
    elements.changeRepoBtn.addEventListener('click', showSetup);

    elements.filterCheckbox.addEventListener('change', (e) => {
        state.filterByFile = e.target.checked;
        loadCommits();
    });

    elements.btnUnified.addEventListener('click', () => {
        setViewMode('unified');
        if (state.selectedCommit) {
            loadCommitDiff(state.selectedCommit);
        }
    });

    elements.btnFile.addEventListener('click', () => {
        setViewMode('file');
        if (state.selectedFile) {
            loadFileContent(state.selectedFile);
        }
    });

    // Allow Enter key to connect
    [elements.repoUrlInput, elements.basePathInput, elements.tokenInput].forEach(input => {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleConnect();
        });
    });
}

function loadConfig() {
    try {
        const saved = localStorage.getItem(CACHE_KEY);
        if (saved) {
            const config = JSON.parse(saved);
            if (config.owner && config.repo) {
                elements.repoUrlInput.value = `${config.owner}/${config.repo}`;
                elements.basePathInput.value = config.basePath || '';
                elements.tokenInput.value = config.token || '';
            }
        }
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

function saveConfig() {
    try {
        const config = {
            owner: state.owner,
            repo: state.repo,
            basePath: state.basePath,
            token: state.token
        };
        localStorage.setItem(CACHE_KEY, JSON.stringify(config));
    } catch (error) {
        console.error('Error saving config:', error);
    }
}

function showSetup() {
    elements.repoSetup.style.display = 'flex';
    elements.mainContent.style.display = 'none';
}

function showMain() {
    elements.repoSetup.style.display = 'none';
    elements.mainContent.style.display = 'flex';
    elements.currentRepoSpan.textContent = `${state.owner}/${state.repo}`;
}

function showError(message) {
    elements.setupError.textContent = message;
    elements.setupError.style.display = 'block';
}

function hideError() {
    elements.setupError.style.display = 'none';
}

// GitHub API Functions
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
        const error = await response.json();
        throw new Error(error.message || `GitHub API error: ${response.status}`);
    }

    return response.json();
}

function parseRepoUrl(url) {
    // Handle formats:
    // - username/repo
    // - https://github.com/username/repo
    // - https://github.com/username/repo.git

    url = url.trim();

    // Remove .git suffix
    url = url.replace(/\.git$/, '');

    // Extract owner/repo
    const match = url.match(/(?:github\.com\/)?([^\/]+)\/([^\/]+)/);

    if (!match) {
        throw new Error('Invalid repository URL format');
    }

    return {
        owner: match[1],
        repo: match[2]
    };
}

async function handleConnect() {
    hideError();
    elements.connectBtn.disabled = true;
    elements.connectBtn.textContent = 'Connecting...';

    try {
        const repoUrl = elements.repoUrlInput.value;
        const { owner, repo } = parseRepoUrl(repoUrl);

        state.owner = owner;
        state.repo = repo;
        state.basePath = elements.basePathInput.value.trim();
        state.token = elements.tokenInput.value.trim();

        // Verify repository access
        await githubApi(`/repos/${owner}/${repo}`);

        // Save config
        saveConfig();

        // Show main interface
        showMain();

        // Load data
        await Promise.all([
            loadFiles(),
            loadCommits()
        ]);

    } catch (error) {
        showError(error.message);
    } finally {
        elements.connectBtn.disabled = false;
        elements.connectBtn.textContent = 'Connect Repository';
    }
}

async function loadFiles() {
    try {
        elements.fileList.innerHTML = '<div class="loading">Loading files...</div>';

        // Get repository tree
        const path = state.basePath ? `?recursive=1` : '?recursive=1';
        const data = await githubApi(`/repos/${state.owner}/${state.repo}/git/trees/HEAD${path}`);

        // Filter for text/markdown files in the base path
        const files = data.tree
            .filter(item => {
                if (item.type !== 'blob') return false;

                const isTextFile = /\.(txt|md)$/i.test(item.path);

                if (state.basePath) {
                    return isTextFile && item.path.startsWith(state.basePath);
                }

                return isTextFile;
            })
            .map(item => ({
                name: item.path.split('/').pop(),
                path: item.path,
                sha: item.sha,
                size: item.size || 0
            }))
            .sort((a, b) => a.name.localeCompare(b.name));

        state.files = files;
        renderFiles();

    } catch (error) {
        elements.fileList.innerHTML = `<div class="error-message">Error loading files: ${error.message}</div>`;
    }
}

async function loadCommits() {
    try {
        elements.commitList.innerHTML = '<div class="loading">Loading commits...</div>';

        let endpoint = `/repos/${state.owner}/${state.repo}/commits?per_page=50`;

        if (state.filterByFile && state.selectedFile) {
            endpoint += `&path=${state.selectedFile}`;
        } else if (state.basePath) {
            endpoint += `&path=${state.basePath}`;
        }

        const commits = await githubApi(endpoint);

        state.commits = commits.map(commit => ({
            sha: commit.sha,
            short_sha: commit.sha.substring(0, 7),
            message: commit.commit.message,
            author: commit.commit.author.name,
            email: commit.commit.author.email,
            date: commit.commit.author.date,
            timestamp: new Date(commit.commit.author.date).getTime()
        }));

        renderCommits();

    } catch (error) {
        elements.commitList.innerHTML = `<div class="error-message">Error loading commits: ${error.message}</div>`;
    }
}

async function loadFileContent(filepath) {
    try {
        elements.contentArea.innerHTML = '<div class="loading">Loading file...</div>';

        const data = await githubApi(`/repos/${state.owner}/${state.repo}/contents/${filepath}`);

        // Decode base64 content
        const content = atob(data.content);

        renderFileContent(content);

    } catch (error) {
        elements.contentArea.innerHTML = `<div class="error-message">Error loading file: ${error.message}</div>`;
    }
}

async function loadCommitDiff(sha) {
    try {
        elements.contentArea.innerHTML = '<div class="loading">Loading diff...</div>';

        // Get commit details with diff
        const commit = await githubApi(`/repos/${state.owner}/${state.repo}/commits/${sha}`, {
            headers: {
                'Accept': 'application/vnd.github.v3.diff'
            }
        });

        // Note: When Accept header is set to diff, response is text
        const response = await fetch(`${GITHUB_API}/repos/${state.owner}/${state.repo}/commits/${sha}`, {
            headers: {
                'Accept': 'application/vnd.github.v3.diff',
                ...(state.token ? { 'Authorization': `token ${state.token}` } : {})
            }
        });

        const diffText = await response.text();

        // Get commit info separately
        const commitInfo = await githubApi(`/repos/${state.owner}/${state.repo}/commits/${sha}`);

        renderDiff({
            commit: {
                sha: commitInfo.sha,
                author: commitInfo.commit.author.name,
                message: commitInfo.commit.message,
                date: commitInfo.commit.author.date
            },
            diff: diffText
        });

    } catch (error) {
        elements.contentArea.innerHTML = `<div class="error-message">Error loading diff: ${error.message}</div>`;
    }
}

// Render Functions
function renderFiles() {
    if (state.files.length === 0) {
        elements.fileList.innerHTML = '<div class="loading">No text files found</div>';
        return;
    }

    elements.fileList.innerHTML = '';

    state.files.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        if (state.selectedFile === file.path) {
            fileItem.classList.add('active');
        }

        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name;

        const fileMeta = document.createElement('div');
        fileMeta.className = 'file-meta';
        fileMeta.textContent = formatFileSize(file.size);

        fileItem.appendChild(fileName);
        fileItem.appendChild(fileMeta);

        fileItem.addEventListener('click', () => selectFile(file));

        elements.fileList.appendChild(fileItem);
    });
}

function renderCommits() {
    if (state.commits.length === 0) {
        elements.commitList.innerHTML = '<div class="loading">No commits found</div>';
        return;
    }

    elements.commitList.innerHTML = '';

    state.commits.forEach(commit => {
        const commitItem = document.createElement('div');
        commitItem.className = 'commit-item';
        if (state.selectedCommit === commit.sha) {
            commitItem.classList.add('active');
        }

        const hash = document.createElement('div');
        hash.className = 'commit-hash';
        hash.textContent = commit.short_sha;

        const message = document.createElement('div');
        message.className = 'commit-message';
        message.textContent = truncate(commit.message.split('\n')[0], 80);

        const meta = document.createElement('div');
        meta.className = 'commit-meta';
        meta.textContent = `${commit.author} • ${formatDate(commit.date)}`;

        commitItem.appendChild(hash);
        commitItem.appendChild(message);
        commitItem.appendChild(meta);

        commitItem.addEventListener('click', () => selectCommit(commit));

        elements.commitList.appendChild(commitItem);
    });
}

function renderFileContent(content) {
    const container = document.createElement('div');
    container.className = 'file-content';
    container.textContent = content;
    elements.contentArea.innerHTML = '';
    elements.contentArea.appendChild(container);
}

function renderDiff(diffData) {
    const container = document.createElement('div');
    container.className = 'diff-container';

    // Parse the unified diff into files
    const files = parseUnifiedDiff(diffData.diff);

    // Filter for text/md files in basePath
    const filteredFiles = files.filter(file => {
        const isTextFile = /\.(txt|md)$/i.test(file.path);
        if (state.basePath) {
            return isTextFile && file.path.startsWith(state.basePath);
        }
        return isTextFile;
    });

    if (filteredFiles.length === 0) {
        container.innerHTML = '<div class="loading">No changes to text files in this commit</div>';
    } else {
        filteredFiles.forEach(file => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'diff-file';

            const header = document.createElement('div');
            header.className = 'diff-header';
            header.textContent = `📄 ${file.path}`;

            const body = document.createElement('div');
            body.className = 'diff-body';

            file.lines.forEach(line => {
                const lineDiv = document.createElement('div');
                lineDiv.className = `diff-line ${line.type}`;

                const lineNumber = document.createElement('span');
                lineNumber.className = 'line-number';
                lineNumber.textContent = line.lineNum || '';

                const lineContent = document.createElement('span');
                lineContent.className = 'line-content';
                lineContent.textContent = line.content;

                lineDiv.appendChild(lineNumber);
                lineDiv.appendChild(lineContent);
                body.appendChild(lineDiv);
            });

            fileDiv.appendChild(header);
            fileDiv.appendChild(body);
            container.appendChild(fileDiv);
        });
    }

    elements.contentArea.innerHTML = '';
    elements.contentArea.appendChild(container);
}

// Diff Parser
function parseUnifiedDiff(diffText) {
    const files = [];
    const lines = diffText.split('\n');
    let currentFile = null;
    let oldLineNum = 0;
    let newLineNum = 0;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        if (line.startsWith('diff --git')) {
            // New file
            if (currentFile) {
                files.push(currentFile);
            }

            const match = line.match(/diff --git a\/(.*?) b\/(.*?)$/);
            currentFile = {
                path: match ? match[2] : 'unknown',
                lines: []
            };
            oldLineNum = 0;
            newLineNum = 0;
        } else if (currentFile && line.startsWith('@@')) {
            // Hunk header
            const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/);
            if (match) {
                oldLineNum = parseInt(match[1]);
                newLineNum = parseInt(match[2]);
            }
            currentFile.lines.push({
                type: 'hunk-header',
                content: line,
                lineNum: ''
            });
        } else if (currentFile && line.startsWith('+') && !line.startsWith('+++')) {
            // Added line
            currentFile.lines.push({
                type: 'add',
                content: line.substring(1),
                lineNum: newLineNum
            });
            newLineNum++;
        } else if (currentFile && line.startsWith('-') && !line.startsWith('---')) {
            // Removed line
            currentFile.lines.push({
                type: 'remove',
                content: line.substring(1),
                lineNum: oldLineNum
            });
            oldLineNum++;
        } else if (currentFile && line.startsWith(' ')) {
            // Context line
            currentFile.lines.push({
                type: 'context',
                content: line.substring(1),
                lineNum: newLineNum
            });
            oldLineNum++;
            newLineNum++;
        }
    }

    if (currentFile) {
        files.push(currentFile);
    }

    return files;
}

// Selection Handlers
function selectFile(file) {
    state.selectedFile = file.path;
    elements.currentFile.textContent = file.path;

    renderFiles();

    if (state.viewMode === 'file') {
        loadFileContent(file.path);
    }

    if (state.filterByFile) {
        loadCommits();
    }
}

function selectCommit(commit) {
    state.selectedCommit = commit.sha;
    renderCommits();

    if (state.viewMode === 'unified') {
        loadCommitDiff(commit.sha);
    }
}

function setViewMode(mode) {
    state.viewMode = mode;
    elements.btnUnified.classList.toggle('active', mode === 'unified');
    elements.btnFile.classList.toggle('active', mode === 'file');
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;

    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        if (hours === 0) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        }
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

function truncate(str, maxLength) {
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength) + '...';
}

// Start the application
init();
