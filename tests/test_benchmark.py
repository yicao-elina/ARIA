"""Tests for aria.evaluation.benchmark module."""

import json
import os
import tempfile
import pytest
from pathlib import Path

from aria.evaluation.benchmark import BenchmarkRunner


@pytest.fixture
def sample_task_file(tmp_path):
    """Create a temporary benchmark task file."""
    tasks = [
        {
            "id": "fwd_test_001",
            "task": "forward_prediction",
            "input": {"method": "CVD", "temperature_c": 750, "material": "MoS2"},
            "target_property": "carrier mobility",
            "expected_outcome": "moderate to high mobility",
            "domain": "in_distribution",
        },
        {
            "id": "fwd_test_002",
            "task": "forward_prediction",
            "input": {"method": "CVD", "temperature_c": 600, "material": "WS2"},
            "target_property": "band gap",
            "expected_outcome": "direct bandgap around 2 eV",
            "domain": "in_distribution",
        },
    ]
    task_file = tmp_path / "test_tasks.jsonl"
    with open(task_file, "w") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")
    return str(task_file)


class TestBenchmarkRunnerInit:
    """Test BenchmarkRunner initialization."""

    def test_init_with_defaults(self):
        """BenchmarkRunner can be created with defaults."""
        runner = BenchmarkRunner()
        assert runner is not None
        assert runner.models == ["qwen2:7b"]
        assert runner.modes == ["baseline", "naive_kg", "aria"]

    def test_init_with_custom_params(self):
        """BenchmarkRunner accepts custom parameters."""
        runner = BenchmarkRunner(
            models=["deepseek-r1:8b"],
            modes=["aria", "aria_full"],
        )
        assert runner.models == ["deepseek-r1:8b"]
        assert runner.modes == ["aria", "aria_full"]


class TestLoadTasks:
    """Test loading benchmark tasks."""

    def test_load_jsonl(self, sample_task_file):
        """Can load tasks from JSONL file."""
        runner = BenchmarkRunner()
        tasks = runner._load_tasks(sample_task_file)
        assert len(tasks) == 2
        assert tasks[0]["id"] == "fwd_test_001"
        assert tasks[1]["task"] == "forward_prediction"

    def test_load_nonexistent_file(self):
        """Raises error for nonexistent file."""
        runner = BenchmarkRunner()
        with pytest.raises(FileNotFoundError):
            runner._load_tasks("/nonexistent/path.jsonl")


class TestTaskValidation:
    """Test task format validation."""

    def test_valid_task(self):
        """Valid task passes validation."""
        runner = BenchmarkRunner()
        task = {
            "id": "test_001",
            "task": "forward_prediction",
            "input": {"material": "MoS2"},
        }
        assert runner._validate_task(task) is True

    def test_missing_id(self):
        """Task without id fails validation."""
        runner = BenchmarkRunner()
        task = {"task": "forward_prediction"}
        assert runner._validate_task(task) is False