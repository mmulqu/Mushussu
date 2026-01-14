from letta_client import Letta
import os

# Configuration
LETTA_URL = "http://localhost:8283"
AGENT_ID = "agent-8e040bc9-419c-46fb-b9f8-5e807af4699e"
FOLDER_NAME = "thoth-workspace"
LOCAL_PATH = r"C:\Users\Mike\PycharmProjects\Thoth\Novel_original"
FILE_EXTENSIONS = ('.py', '.md', '.txt', '.json')

client = Letta(base_url=LETTA_URL)

# Get or create folder
folders = client.folders.list()
folder = next((f for f in folders if f.name == FOLDER_NAME), None)

if not folder:
    folder = client.folders.create(
        name=FOLDER_NAME,
        embedding_config={
            "embedding_endpoint_type": "openai",
            "embedding_model": "text-embedding-3-small",
            "embedding_dim": 1536,
            "embedding_chunk_size": 300
        }
    )
    print(f"Created folder: {folder.id}")
else:
    print(f"Found existing folder: {folder.id}")

# Upload files
for filename in os.listdir(LOCAL_PATH):
    if filename.endswith(FILE_EXTENSIONS):
        filepath = os.path.join(LOCAL_PATH, filename)
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                client.folders.files.upload(folder_id=folder.id, file=f)
                print(f"Uploaded: {filename}")

# Attach to agent
client.agents.folders.attach(agent_id=AGENT_ID, folder_id=folder.id)
print(f"Done! Folder {folder.id} attached to agent {AGENT_ID}")