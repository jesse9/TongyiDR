import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
from tqdm import tqdm
import threading
from datetime import datetime
from react_agent import MultiTurnReactAgent
import time
import math

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question", help="The question to answer")
    parser.add_argument("--model", type=str, default="")
    parser.add_argument("--output", type=str, default="./output")
    parser.add_argument("--fileroot", type=str, default="./inference/eval_data/file_corpus/")
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--top_p", type=float, default=0.95)
    parser.add_argument("--presence_penalty", type=float, default=1.1)
    parser.add_argument("--max_workers", type=int, default=1)
    parser.add_argument("--openrouter_model", type=str, default="alibaba/tongyi-deepresearch-30b-a3b")
    args = parser.parse_args()

    model = args.model
    output_base = args.output
    roll_out_count = 1  # Fixed to 1 for single execution

    # Get OpenRouter model name from command line argument
    openrouter_model = args.openrouter_model

    if not model and openrouter_model:
        model_name = "openrouter"
        model_dir = os.path.join(output_base, "openrouter_output")
    else:
        model_name = os.path.basename(model.rstrip('/'))
        model_dir = os.path.join(output_base, f"{model_name}_sglang")

    # Create a simple dataset name based on timestamp for single question
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_dir = os.path.join(model_dir, f"single_question_{timestamp}")

    os.makedirs(dataset_dir, exist_ok=True)

    print(f"Model name: {model_name}")
    print(f"Output directory: {dataset_dir}")
    print(f"Question: {args.question}")

    # Create single item from command line question
    item = {
        "question": args.question,
        "answer": ""  # Not used in single execution mode
    }

    # Prepare tasks
    output_files = {1: os.path.join(dataset_dir, "output.jsonl")}

    tasks_to_run_all = []
    # For single execution, we don't need to check for existing results
    # Use a dummy port since OpenRouter doesn't need actual ports
    planning_port = 6001 if model else 9999  # Dummy port for OpenRouter mode
    tasks_to_run_all.append({
        "item": item,
        "rollout_idx": 1,
        "planning_port": planning_port,
    })

    if not tasks_to_run_all:
        print("No tasks to run.")
    else:
        if not model and openrouter_model:
            llm_cfg = {
                'model': "openrouter",  # Placeholder, actual model name handled in react_agent.py
                'openrouter_model': openrouter_model,
                'generate_cfg': {
                    'max_input_tokens': 320000,
                    'max_retries': 10,
                    'temperature': args.temperature,
                    'top_p': args.top_p,
                    'presence_penalty': args.presence_penalty
                },
                'model_type': 'openrouter'
            }
        else:
            llm_cfg = {
                'model': model,
                'generate_cfg': {
                    'max_input_tokens': 320000,
                    'max_retries': 10,
                    'temperature': args.temperature,
                    'top_p': args.top_p,
                    'presence_penalty': args.presence_penalty
                },
                'model_type': 'qwen_dashscope'
            }

        test_agent = MultiTurnReactAgent(
            llm=llm_cfg,
            function_list=["search", "visit", "google_scholar", "PythonInterpreter"],
            file_root_path=args.fileroot
        )

        write_locks = {1: threading.Lock()}

        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_task = {
                executor.submit(
                    test_agent._run,
                    task,
                    model
                ): task for task in tasks_to_run_all
            }

            for future in tqdm(as_completed(future_to_task), total=len(tasks_to_run_all), desc="Processing"):
                task_info = future_to_task[future]
                rollout_idx = task_info["rollout_idx"]
                output_file = output_files[rollout_idx]
                try:
                    result = future.result()
                    with write_locks[rollout_idx]:
                        with open(output_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    print(f"Result saved to {output_file}")
                except concurrent.futures.TimeoutError:
                    question = task_info["item"].get("question", "")
                    print(f'Timeout (>1800s): "{question}" (Rollout {rollout_idx})')
                    future.cancel()
                    error_result = {
                        "question": question,
                        "answer": task_info["item"].get("answer", ""),
                        "rollout_idx": rollout_idx,
                        "rollout_id": rollout_idx,
                        "error": "Timeout (>1800s)",
                        "messages": [],
                        "prediction": "[Failed]"
                    }
                    with write_locks[rollout_idx]:
                        with open(output_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(error_result, ensure_ascii=False) + "\n")
                except Exception as exc:
                    question = task_info["item"].get("question", "")
                    print(f'Task for question "{question}" (Rollout {rollout_idx}) generated an exception: {exc}')
                    error_result = {
                        "question": question,
                        "answer": task_info["item"].get("answer", ""),
                        "rollout_idx": rollout_idx,
                        "rollout_id": rollout_idx,
                        "error": f"Future resolution failed: {exc}",
                        "messages": [],
                        "prediction": "[Failed]",
                    }
                    print("===============================")
                    print(error_result)
                    print("===============================")
                    with write_locks[rollout_idx]:
                        with open(output_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(error_result, ensure_ascii=False) + "\n")

        print("\nExecution completed!")
