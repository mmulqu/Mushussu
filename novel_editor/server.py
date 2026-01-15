#!/usr/bin/env python3
"""
Lightweight Flask server for novel diff visualization.
Provides git operations for the frontend editor.
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import git
import os
from pathlib import Path
import difflib
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# Repository path - defaults to parent directory
REPO_PATH = os.environ.get('REPO_PATH', '/home/user/Mushussu')
NOVEL_DIR = 'Novel_original'


def get_repo():
    """Get git repository object."""
    return git.Repo(REPO_PATH)


@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('static', 'index.html')


@app.route('/api/files')
def list_files():
    """List all novel files (.txt and .md) in the Novel_original directory."""
    novel_path = Path(REPO_PATH) / NOVEL_DIR

    files = []
    if novel_path.exists():
        for file_path in sorted(novel_path.glob('*')):
            if file_path.suffix in ['.txt', '.md']:
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'path': f'{NOVEL_DIR}/{file_path.name}',
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

    return jsonify({'files': files})


@app.route('/api/file/<path:filepath>')
def get_file(filepath):
    """Get contents of a specific file."""
    try:
        file_path = Path(REPO_PATH) / filepath
        if not file_path.exists() or not file_path.is_relative_to(REPO_PATH):
            return jsonify({'error': 'File not found'}), 404

        content = file_path.read_text(encoding='utf-8')
        return jsonify({'content': content, 'path': filepath})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/commits')
def list_commits():
    """List all commits, with option to filter by file."""
    try:
        repo = get_repo()
        file_path = request.args.get('file')
        limit = int(request.args.get('limit', 50))

        commits = []

        if file_path:
            # Filter commits that modified this specific file
            commit_iter = repo.iter_commits(paths=file_path, max_count=limit)
        else:
            commit_iter = repo.iter_commits(max_count=limit)

        for commit in commit_iter:
            commits.append({
                'hash': commit.hexsha,
                'short_hash': commit.hexsha[:7],
                'author': commit.author.name,
                'email': commit.author.email,
                'message': commit.message.strip(),
                'date': datetime.fromtimestamp(commit.committed_date).isoformat(),
                'timestamp': commit.committed_date
            })

        return jsonify({'commits': commits})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/diff/<commit_hash>')
def get_commit_diff(commit_hash):
    """Get diff for a specific commit."""
    try:
        repo = get_repo()
        commit = repo.commit(commit_hash)

        # Get parent commit for diff
        if commit.parents:
            parent = commit.parents[0]
            diff_index = parent.diff(commit, create_patch=True)
        else:
            # First commit - diff against empty tree
            diff_index = commit.diff(git.NULL_TREE, create_patch=True)

        diffs = []
        for diff in diff_index:
            if diff.a_path and (diff.a_path.endswith('.txt') or diff.a_path.endswith('.md')):
                diff_data = {
                    'file': diff.a_path or diff.b_path,
                    'change_type': diff.change_type,
                    'diff': diff.diff.decode('utf-8', errors='ignore') if diff.diff else ''
                }
                diffs.append(diff_data)

        return jsonify({
            'commit': {
                'hash': commit.hexsha,
                'author': commit.author.name,
                'message': commit.message.strip(),
                'date': datetime.fromtimestamp(commit.committed_date).isoformat()
            },
            'diffs': diffs
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/diff/compare')
def compare_versions():
    """Compare two versions of a file."""
    try:
        file_path = request.args.get('file')
        commit1 = request.args.get('from', 'HEAD~1')
        commit2 = request.args.get('to', 'HEAD')

        if not file_path:
            return jsonify({'error': 'File path required'}), 400

        repo = get_repo()

        # Get file content at each commit
        try:
            content1 = repo.git.show(f'{commit1}:{file_path}')
        except git.exc.GitCommandError:
            content1 = ''

        try:
            content2 = repo.git.show(f'{commit2}:{file_path}')
        except git.exc.GitCommandError:
            content2 = ''

        # Generate unified diff
        diff = list(difflib.unified_diff(
            content1.splitlines(keepends=True),
            content2.splitlines(keepends=True),
            fromfile=f'{file_path} ({commit1})',
            tofile=f'{file_path} ({commit2})',
            lineterm=''
        ))

        return jsonify({
            'file': file_path,
            'from': commit1,
            'to': commit2,
            'diff': ''.join(diff)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/file/history/<path:filepath>')
def file_history(filepath):
    """Get change history for a specific file."""
    try:
        repo = get_repo()
        commits = []

        for commit in repo.iter_commits(paths=filepath, max_count=100):
            commits.append({
                'hash': commit.hexsha,
                'short_hash': commit.hexsha[:7],
                'author': commit.author.name,
                'message': commit.message.strip(),
                'date': datetime.fromtimestamp(commit.committed_date).isoformat(),
                'timestamp': commit.committed_date
            })

        return jsonify({
            'file': filepath,
            'commits': commits
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"Starting novel editor server...")
    print(f"Repository: {REPO_PATH}")
    print(f"Novel directory: {NOVEL_DIR}")
    app.run(debug=True, host='0.0.0.0', port=5000)
