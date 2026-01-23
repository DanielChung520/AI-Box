import json

config_path = "config/config.json"

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# 更新 knowledge_graph_extraction 優先級
kg_priority = [
    {
        "model": "qwen3-coder:30b",
        "context_size": 32000,
        "max_tokens": 8192,
        "temperature": 0.2,
        "timeout": 180,
        "retries": 2,
        "rpm": 30,
        "concurrency": 3,
    },
    {
        "model": "mistral-nemo:12b",
        "context_size": 32000,
        "max_tokens": 8192,
        "temperature": 0.2,
        "timeout": 200,
        "retries": 2,
        "rpm": 20,
        "concurrency": 2,
    },
    {
        "model": "qwen3-next:latest",
        "context_size": 32000,
        "max_tokens": 8192,
        "temperature": 0.2,
        "timeout": 180,
        "retries": 2,
        "rpm": 30,
        "concurrency": 3,
    },
]

config["services"]["moe"]["model_priority"]["knowledge_graph_extraction"]["priority"] = kg_priority

# 同步更新 text_analysis 的默認模型 (NER, RT)
config["text_analysis"]["ner"]["model_name"] = "qwen3-coder:30b"
config["text_analysis"]["rt"]["model_name"] = "qwen3-coder:30b"

# 寫回文件
with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("Successfully updated config/config.json")
