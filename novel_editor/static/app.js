// Novel Diff Viewer - Main Application Logic

const API_BASE = 'http://localhost:5000/api';

// Application state
const state = {
    files: [],
    commits: [],
    selectedFile: null,
    selectedCommit: null,
    viewMode: 'unified', // 'unified', 'split', 'file'
    filterByFile: false
};

// DOM Elements
const elements = {
    fileList: document.getElementById('file-list'),
    commitList: document.getElementById('commit-list'),
    contentArea: document.getElementById('content-area'),
    currentFile: document.getElementById('current-file'),
    filterCheckbox: document.getElementById('filter-current-file'),
    btnUnified: document.getElementById('btn-unified'),
    btnSplit: document.getElementById('btn-split'),
    btnFile: document.getElementById('btn-file')
};

// Initialize application
async function init() {
    setupEventListeners();
    await loadFiles();
    await loadCommits();
}

// Event Listeners
function setupEventListeners() {
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

    elements.btnSplit.addEventListener('click', () => {
        setViewMode('split');
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
}

function setViewMode(mode) {
    state.viewMode = mode;
    elements.btnUnified.classList.toggle('active', mode === 'unified');
    elements.btnSplit.classList.toggle('active', mode === 'split');
    elements.btnFile.classList.toggle('active', mode === 'file');
}

// API Functions
async function loadFiles() {
    try {
        elements.fileList.innerHTML = '<div class="loading">Loading files...</div>';
        const response = await fetch(`${API_BASE}/files`);
        const data = await response.json();

        state.files = data.files;
        renderFiles();
    } catch (error) {
        elements.fileList.innerHTML = `<div class="error">Error loading files: ${error.message}</div>`;
    }
}

async function loadCommits() {
    try {
        elements.commitList.innerHTML = '<div class="loading">Loading commits...</div>';

        let url = `${API_BASE}/commits?limit=50`;
        if (state.filterByFile && state.selectedFile) {
            url += `&file=${state.selectedFile}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        state.commits = data.commits;
        renderCommits();
    } catch (error) {
        elements.commitList.innerHTML = `<div class="error">Error loading commits: ${error.message}</div>`;
    }
}

async function loadFileContent(filepath) {
    try {
        elements.contentArea.innerHTML = '<div class="loading">Loading file...</div>';
        const response = await fetch(`${API_BASE}/file/${filepath}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        renderFileContent(data.content);
    } catch (error) {
        elements.contentArea.innerHTML = `<div class="error">Error loading file: ${error.message}</div>`;
    }
}

async function loadCommitDiff(commitHash) {
    try {
        elements.contentArea.innerHTML = '<div class="loading">Loading diff...</div>';
        const response = await fetch(`${API_BASE}/diff/${commitHash}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        renderDiff(data);
    } catch (error) {
        elements.contentArea.innerHTML = `<div class="error">Error loading diff: ${error.message}</div>`;
    }
}

async function loadFileHistory(filepath) {
    try {
        const response = await fetch(`${API_BASE}/file/history/${filepath}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        state.commits = data.commits;
        renderCommits();
    } catch (error) {
        console.error('Error loading file history:', error);
    }
}

// Render Functions
function renderFiles() {
    if (state.files.length === 0) {
        elements.fileList.innerHTML = '<div class="loading">No files found</div>';
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
        const size = formatFileSize(file.size);
        fileMeta.textContent = size;

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
        if (state.selectedCommit === commit.hash) {
            commitItem.classList.add('active');
        }

        const hash = document.createElement('div');
        hash.className = 'commit-hash';
        hash.textContent = commit.short_hash;

        const message = document.createElement('div');
        message.className = 'commit-message';
        message.textContent = truncate(commit.message, 60);

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

    if (diffData.diffs.length === 0) {
        container.innerHTML = '<div class="loading">No changes in this commit for novel files</div>';
    }

    diffData.diffs.forEach(diff => {
        const fileDiv = document.createElement('div');
        fileDiv.className = 'diff-file';

        const header = document.createElement('div');
        header.className = 'diff-header';
        header.textContent = `📄 ${diff.file}`;

        const body = document.createElement('div');
        body.className = 'diff-body';

        // Parse unified diff
        const lines = diff.diff.split('\n');
        const diffLines = parseDiff(lines);

        diffLines.forEach(line => {
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

    elements.contentArea.innerHTML = '';
    elements.contentArea.appendChild(container);
}

// Diff Parser
function parseDiff(lines) {
    const result = [];
    let oldLineNum = 0;
    let newLineNum = 0;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        if (line.startsWith('@@')) {
            // Hunk header
            const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/);
            if (match) {
                oldLineNum = parseInt(match[1]);
                newLineNum = parseInt(match[2]);
            }
            result.push({
                type: 'hunk-header',
                content: line,
                lineNum: ''
            });
        } else if (line.startsWith('+') && !line.startsWith('+++')) {
            // Added line
            result.push({
                type: 'add',
                content: line.substring(1),
                lineNum: newLineNum
            });
            newLineNum++;
        } else if (line.startsWith('-') && !line.startsWith('---')) {
            // Removed line
            result.push({
                type: 'remove',
                content: line.substring(1),
                lineNum: oldLineNum
            });
            oldLineNum++;
        } else if (line.startsWith(' ')) {
            // Context line
            result.push({
                type: 'context',
                content: line.substring(1),
                lineNum: newLineNum
            });
            oldLineNum++;
            newLineNum++;
        } else if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('diff')) {
            // Skip diff metadata
            continue;
        } else if (line.trim() !== '') {
            // Other content
            result.push({
                type: 'context',
                content: line,
                lineNum: ''
            });
        }
    }

    return result;
}

// Selection Handlers
function selectFile(file) {
    state.selectedFile = file.path;
    elements.currentFile.textContent = file.path;

    // Update UI
    renderFiles();

    // Load file content if in file view mode
    if (state.viewMode === 'file') {
        loadFileContent(file.path);
    }

    // Reload commits if filtering is enabled
    if (state.filterByFile) {
        loadCommits();
    } else {
        // Load file history in commits panel
        loadFileHistory(file.path);
    }
}

function selectCommit(commit) {
    state.selectedCommit = commit.hash;
    renderCommits();

    // Load diff
    if (state.viewMode === 'unified' || state.viewMode === 'split') {
        loadCommitDiff(commit.hash);
    }
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

    // Less than 1 day
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        if (hours === 0) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes}m ago`;
        }
        return `${hours}h ago`;
    }

    // Less than 7 days
    if (diff < 604800000) {
        const days = Math.floor(diff / 86400000);
        return `${days}d ago`;
    }

    // Format as date
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
