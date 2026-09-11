from __future__ import annotations

from pathlib import Path

import yaml

from app.runners.llama_bench import summarize_llama_bench_rows


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_performance_v1_recipe_defines_formal_matrix():
    recipe = yaml.safe_load((PROJECT_ROOT / "recipes/performance-v1.yaml").read_text(encoding="utf-8"))
    config = recipe["config"]
    assert recipe["suite"] == "performance"
    assert config["prompt_tokens"] == [512, 2048, 8192, 32768]
    assert config["gen_tokens"] == [512]
    assert config["repetitions"] == 5
    assert config["n_gpu_layers"] == 999
    assert config["batch_size"] == 2048
    assert config["ubatch_size"] == 512
    assert config["flash_attn"] is True


def test_formal_performance_summary_preserves_stats_and_repetitions():
    rows = [
        {
            "n_prompt": 512,
            "n_gen": 0,
            "avg_ts": 10.0,
            "stddev_ts": 1.5811,
            "samples_ts": [8.0, 9.0, 10.0, 11.0, 12.0],
            "avg_ns": 512000000,
            "stddev_ns": 1000000,
        },
        {
            "n_prompt": 0,
            "n_gen": 512,
            "avg_ts": 20.0,
            "stddev_ts": 0.0,
            "samples_ts": [20.0, 20.0, 20.0, 20.0, 20.0],
            "avg_ns": 25600000000,
            "stddev_ns": 0,
        },
    ]
    summary = summarize_llama_bench_rows(rows)
    assert summary["repetitions"] == 5
    assert summary["representative"]["pp_512"]["mean"] == 10.0
    assert summary["representative"]["pp_512"]["stddev"] == 1.5811
    assert summary["representative"]["pp_512"]["repetitions"] == [8.0, 9.0, 10.0, 11.0, 12.0]
    assert summary["representative"]["tg_512"]["mean"] == 20.0
    assert summary["representative"]["tg_512"]["repetitions"] == [20.0] * 5
