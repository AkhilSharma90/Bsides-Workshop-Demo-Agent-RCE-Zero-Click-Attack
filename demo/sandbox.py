"""
Docker-based sandboxed command executor for realistic RCE demonstration.

This module provides safe execution of commands in isolated Docker containers
with strict resource limits and no network access.
"""

from __future__ import annotations

import subprocess
from typing import Dict, Optional


class SandboxedExecutor:
    """
    Executes commands in isolated Docker containers with safety controls.

    Safety features:
    - No network access (--network none)
    - Read-only filesystem (--read-only)
    - Memory limit (128MB)
    - CPU quota (50% of one core)
    - Short-lived containers (auto-remove)
    - Non-root user
    - Command allowlist (enforced by safe-exec)
    """

    def __init__(self, image: str = "bsides-sandbox:latest") -> None:
        self.image = image
        self.timeout_seconds = 5
        self.mem_limit = "128m"
        self.cpu_quota = 50000  # 50% of one core (100000 = 100%)

    def is_available(self) -> bool:
        """Check if Docker is available and the sandbox image exists."""
        try:
            # Check Docker is running
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=2,
                check=False
            )
            if result.returncode != 0:
                return False

            # Check image exists
            result = subprocess.run(
                ["docker", "images", "-q", self.image],
                capture_output=True,
                timeout=2,
                check=False
            )
            return bool(result.stdout.strip())

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def execute(self, command: str) -> Dict[str, any]:
        """
        Execute command in sandboxed Docker container.

        Args:
            command: The command to execute (will be validated by safe-exec)

        Returns:
            Dictionary with status, command, stdout, stderr, and metadata
        """
        if not self.is_available():
            return {
                "status": "error",
                "command": command,
                "error": "Docker not available or sandbox image not found",
                "execution_mode": "sandboxed"
            }

        try:
            # Build Docker run command with safety controls
            docker_cmd = [
                "docker", "run",
                "--rm",  # Auto-remove after execution
                "--network", "none",  # No network access
                "--read-only",  # Read-only filesystem
                "--memory", self.mem_limit,  # Memory limit
                "--cpu-quota", str(self.cpu_quota),  # CPU limit
                "--user", "sandboxuser",  # Non-root user
                "--cap-drop", "ALL",  # Drop all capabilities
                self.image,
                "safe-exec",  # Use safe command executor
                command
            ]

            # Execute with timeout
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=self.timeout_seconds,
                text=True,
                check=False
            )

            if result.returncode == 0:
                return {
                    "status": "success",
                    "command": command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                    "execution_mode": "sandboxed",
                    "container_image": self.image
                }
            else:
                return {
                    "status": "error",
                    "command": command,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                    "error": f"Command failed with exit code {result.returncode}",
                    "execution_mode": "sandboxed"
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "command": command,
                "error": f"Command timed out after {self.timeout_seconds} seconds",
                "execution_mode": "sandboxed"
            }
        except Exception as e:
            return {
                "status": "error",
                "command": command,
                "error": f"Execution failed: {str(e)}",
                "execution_mode": "sandboxed"
            }

    def extract_command_from_target(self, target: str) -> str:
        """
        Extract executable command from target string.

        The target may include the poison token and other noise.
        We extract the actual command to run.

        Args:
            target: Raw target string from action plan

        Returns:
            Cleaned command string
        """
        # Remove poison token
        command = target.replace("WRITE_PWNED_FILE", "").strip()

        # If it starts with serviceA/B, try to extract command after it
        for service in ["serviceA", "serviceB", "serviceC"]:
            if command.startswith(service):
                command = command[len(service):].strip()
                break

        # If we have a recognizable command, use it
        # Otherwise, default to kubectl get pods as a demonstration
        command_keywords = ["kubectl", "aws", "ssh", "curl"]
        if not any(keyword in command.lower() for keyword in command_keywords):
            # Default to a safe demonstration command
            command = "kubectl get pods"

        return command
