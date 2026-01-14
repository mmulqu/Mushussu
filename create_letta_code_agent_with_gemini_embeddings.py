# create_thoth_letta_code.py
from letta_client import Letta

client = Letta(base_url="http://localhost:8283")

# 1. Get Thoth's current memory blocks
old_agent_id = "agent-2dd9458c-2199-4b87-8e74-7a51dc5ae149"
old_blocks = client.agents.blocks.list(agent_id=old_agent_id)

print("Thoth's current memory blocks:")
for block in old_blocks:
    print(f"  - {block.label}: {len(block.value)} chars")

# 2. Deduplicate blocks (keep first occurrence of each label)
seen_labels = set()
unique_blocks = []
for block in old_blocks:
    if block.label not in seen_labels:
        seen_labels.add(block.label)
        unique_blocks.append(block)

print(f"\nUsing {len(unique_blocks)} unique blocks")

# 3. Create new agent with Z.ai LLM + Google AI embeddings
new_agent = client.agents.create(
    name="ThothCode",
    model="glm-4.7",
    model_endpoint="https://api.z.ai/api/coding/paas/v4",
    model_endpoint_type="openai",
    embedding="openai/text-embedding-3-small",
    memory_blocks=[...]
)

print(f"\n✅ New agent created!")
print(f"   ID: {new_agent.id}")
print(f"   Name: {new_agent.name}")
print(f"\nNow run:")
print(f"   letta --agent {new_agent.id}")