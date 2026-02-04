"""
Mock command outputs for realistic attack demonstrations.

This module provides fake but convincing outputs for common DevOps tools
(kubectl, aws, ssh, etc.) to demonstrate what RCE would look like without
actually executing dangerous commands.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MockCommandGenerator:
    """Generates realistic mock outputs for various command-line tools."""

    def __init__(self) -> None:
        self.pod_names = [
            "api-server-7d8f9c4b",
            "worker-5c3a1e8d",
            "redis-cache-9f2b4a",
            "postgres-db-3e7c1f",
            "nginx-proxy-6a9d2b",
        ]
        self.service_names = ["serviceA", "serviceB", "serviceC"]

    def generate(self, target: str) -> Dict[str, any]:
        """
        Generate mock output based on the target command.

        Args:
            target: The command target string (e.g., "serviceA kubectl get pods")

        Returns:
            Dictionary with status, command, output, and stdout
        """
        target_lower = target.lower()

        # Detect command type
        if "kubectl" in target_lower:
            return self._mock_kubectl(target)
        elif "aws" in target_lower:
            return self._mock_aws(target)
        elif "ssh" in target_lower or "exec" in target_lower:
            return self._mock_ssh(target)
        elif "curl" in target_lower:
            return self._mock_curl(target)
        else:
            # Generic command execution
            return self._mock_generic(target)

    def _mock_kubectl(self, target: str) -> Dict[str, any]:
        """Generate mock kubectl command outputs."""
        target_lower = target.lower()

        if "get pods" in target_lower or "get pod" in target_lower:
            return self._mock_kubectl_get_pods(target)
        elif "exec" in target_lower:
            return self._mock_kubectl_exec(target)
        elif "describe" in target_lower:
            return self._mock_kubectl_describe(target)
        elif "logs" in target_lower:
            return self._mock_kubectl_logs(target)
        else:
            return self._mock_kubectl_generic(target)

    def _mock_kubectl_get_pods(self, target: str) -> Dict[str, any]:
        """Mock kubectl get pods output."""
        # Determine namespace
        namespace = "production"
        if "-n " in target or "--namespace" in target:
            parts = target.split()
            for i, part in enumerate(parts):
                if part in ["-n", "--namespace"] and i + 1 < len(parts):
                    namespace = parts[i + 1]

        # Generate pod list
        pods = []
        for pod_name in self.pod_names[:3]:  # Show 3 pods
            age_days = random.randint(1, 30)
            pods.append({
                "metadata": {
                    "name": pod_name,
                    "namespace": namespace,
                    "creationTimestamp": (datetime.utcnow() - timedelta(days=age_days)).isoformat() + "Z"
                },
                "status": {
                    "phase": "Running",
                    "conditions": [
                        {"type": "Ready", "status": "True"}
                    ]
                }
            })

        # Text output
        stdout_lines = ["NAME              READY   STATUS    RESTARTS   AGE"]
        for pod in pods:
            name = pod["metadata"]["name"]
            age_str = f"{(datetime.utcnow() - datetime.fromisoformat(pod['metadata']['creationTimestamp'].replace('Z', ''))).days}d"
            stdout_lines.append(f"{name:<18}1/1     Running   0          {age_str}")

        return {
            "status": "success",
            "command": f"kubectl get pods -n {namespace}",
            "output": {"kind": "PodList", "items": pods},
            "stdout": "\n".join(stdout_lines),
            "execution_mode": "mock-realistic"
        }

    def _mock_kubectl_exec(self, target: str) -> Dict[str, any]:
        """Mock kubectl exec output."""
        # Extract pod name if present
        pod_name = "api-server-7d8f9c4b"
        for pod in self.pod_names:
            if pod in target:
                pod_name = pod
                break

        # Mock command execution inside pod
        stdout = f"""root@{pod_name}:/app# whoami
root
root@{pod_name}:/app# hostname
{pod_name}
root@{pod_name}:/app# ls -la /
total 84
drwxr-xr-x   1 root root 4096 Jan 28 10:15 .
drwxr-xr-x   1 root root 4096 Jan 28 10:15 ..
drwxr-xr-x   2 root root 4096 Dec 15 08:23 app
drwxr-xr-x   2 root root 4096 Dec 15 08:23 bin
drwxr-xr-x   2 root root 4096 Dec 15 08:23 etc
drwxr-xr-x   2 root root 4096 Dec 15 08:23 home
"""

        return {
            "status": "success",
            "command": f"kubectl exec -it {pod_name} -- /bin/sh",
            "output": {"pod": pod_name, "container": "main"},
            "stdout": stdout,
            "execution_mode": "mock-realistic"
        }

    def _mock_kubectl_describe(self, target: str) -> Dict[str, any]:
        """Mock kubectl describe output."""
        pod_name = self.pod_names[0]

        stdout = f"""Name:         {pod_name}
Namespace:    production
Priority:     0
Node:         node-3a7f9d/10.0.1.45
Start Time:   Mon, 28 Jan 2025 10:15:32 +0000
Labels:       app=api-server
              tier=backend
Annotations:  <none>
Status:       Running
IP:           10.244.2.15
Containers:
  main:
    Container ID:   docker://7f8e9a2b3c4d5e6f7g8h9i0j1k2l3m4n
    Image:          api-server:v1.2.3
    Image ID:       docker-pullable://api-server@sha256:abc123
    Port:           8080/TCP
    State:          Running
      Started:      Mon, 28 Jan 2025 10:15:35 +0000
    Ready:          True
    Restart Count:  0
    Environment:
      DB_HOST:      postgres-db-3e7c1f
      REDIS_HOST:   redis-cache-9f2b4a
"""

        return {
            "status": "success",
            "command": f"kubectl describe pod {pod_name}",
            "output": {"name": pod_name, "namespace": "production"},
            "stdout": stdout,
            "execution_mode": "mock-realistic"
        }

    def _mock_kubectl_logs(self, target: str) -> Dict[str, any]:
        """Mock kubectl logs output."""
        pod_name = self.pod_names[0]

        stdout = f"""2025-01-28T10:15:35Z INFO Starting API server on port 8080
2025-01-28T10:15:36Z INFO Connected to database postgres-db-3e7c1f:5432
2025-01-28T10:15:36Z INFO Connected to Redis redis-cache-9f2b4a:6379
2025-01-28T10:15:37Z INFO Health check endpoint ready at /health
2025-01-28T10:15:37Z INFO API server ready to accept requests
2025-01-28T10:16:42Z INFO GET /api/users 200 45ms
2025-01-28T10:17:15Z INFO POST /api/orders 201 123ms
2025-01-28T10:18:03Z WARNING Rate limit approaching for client 192.168.1.50
"""

        return {
            "status": "success",
            "command": f"kubectl logs {pod_name}",
            "output": {"pod": pod_name},
            "stdout": stdout,
            "execution_mode": "mock-realistic"
        }

    def _mock_kubectl_generic(self, target: str) -> Dict[str, any]:
        """Mock generic kubectl command."""
        return {
            "status": "success",
            "command": target,
            "output": {"message": "kubectl command executed"},
            "stdout": "Command completed successfully",
            "execution_mode": "mock-realistic"
        }

    def _mock_aws(self, target: str) -> Dict[str, any]:
        """Generate mock AWS CLI outputs."""
        target_lower = target.lower()

        if "s3 ls" in target_lower:
            return self._mock_aws_s3_ls(target)
        elif "ec2 describe-instances" in target_lower:
            return self._mock_aws_ec2_describe(target)
        elif "ssm start-session" in target_lower:
            return self._mock_aws_ssm(target)
        elif "secrets" in target_lower:
            return self._mock_aws_secrets(target)
        else:
            return self._mock_aws_generic(target)

    def _mock_aws_s3_ls(self, target: str) -> Dict[str, any]:
        """Mock AWS S3 ls output."""
        bucket = "customer-data-prod"
        if "s3://" in target:
            parts = target.split("s3://")
            if len(parts) > 1:
                bucket = parts[1].split()[0].rstrip("/")

        files = [
            {"Key": "backups/2025-01-28.tar.gz", "Size": 10485760, "LastModified": "2025-01-28T06:00:00Z"},
            {"Key": "backups/2025-01-27.tar.gz", "Size": 10223456, "LastModified": "2025-01-27T06:00:00Z"},
            {"Key": "configs/prod.json", "Size": 2048, "LastModified": "2025-01-20T14:30:00Z"},
            {"Key": "logs/app-2025-01-28.log", "Size": 524288, "LastModified": "2025-01-28T10:00:00Z"},
        ]

        stdout_lines = []
        for f in files:
            size_mb = f["Size"] / (1024 * 1024)
            date = f["LastModified"][:10]
            time = f["LastModified"][11:19]
            stdout_lines.append(f"{date} {time} {size_mb:>10.2f} MB {f['Key']}")

        return {
            "status": "success",
            "command": f"aws s3 ls s3://{bucket}/",
            "output": files,
            "stdout": "\n".join(stdout_lines),
            "execution_mode": "mock-realistic"
        }

    def _mock_aws_ec2_describe(self, target: str) -> Dict[str, any]:
        """Mock AWS EC2 describe-instances output."""
        instances = [
            {
                "InstanceId": "i-0a1b2c3d4e5f6g7h8",
                "InstanceType": "t3.large",
                "State": {"Name": "running"},
                "PrivateIpAddress": "10.0.1.45",
                "PublicIpAddress": "54.123.45.67",
                "Tags": [
                    {"Key": "Name", "Value": "api-server-prod-1"},
                    {"Key": "Environment", "Value": "production"}
                ]
            },
            {
                "InstanceId": "i-1b2c3d4e5f6g7h8i9",
                "InstanceType": "t3.medium",
                "State": {"Name": "running"},
                "PrivateIpAddress": "10.0.1.46",
                "PublicIpAddress": "54.123.45.68",
                "Tags": [
                    {"Key": "Name", "Value": "worker-prod-1"},
                    {"Key": "Environment", "Value": "production"}
                ]
            }
        ]

        stdout = f"""INSTANCES	i-0a1b2c3d4e5f6g7h8	t3.large	running	10.0.1.45	54.123.45.67
TAGS	Name	api-server-prod-1
TAGS	Environment	production
INSTANCES	i-1b2c3d4e5f6g7h8i9	t3.medium	running	10.0.1.46	54.123.45.68
TAGS	Name	worker-prod-1
TAGS	Environment	production
"""

        return {
            "status": "success",
            "command": "aws ec2 describe-instances",
            "output": {"Reservations": [{"Instances": instances}]},
            "stdout": stdout,
            "execution_mode": "mock-realistic"
        }

    def _mock_aws_ssm(self, target: str) -> Dict[str, any]:
        """Mock AWS SSM start-session output."""
        instance_id = "i-0a1b2c3d4e5f6g7h8"

        stdout = f"""Starting session with SessionId: admin-0123456789abcdef0
sh-4.2$ whoami
ssm-user
sh-4.2$ hostname
ip-10-0-1-45.ec2.internal
sh-4.2$ sudo su -
root@ip-10-0-1-45:~# id
uid=0(root) gid=0(root) groups=0(root)
"""

        return {
            "status": "success",
            "command": f"aws ssm start-session --target {instance_id}",
            "output": {"SessionId": "admin-0123456789abcdef0", "InstanceId": instance_id},
            "stdout": stdout,
            "execution_mode": "mock-realistic"
        }

    def _mock_aws_secrets(self, target: str) -> Dict[str, any]:
        """Mock AWS Secrets Manager output."""
        secret_name = "prod/database/credentials"

        secret_value = {
            "username": "admin",
            "password": "REDACTED_FOR_DEMO",
            "host": "prod-db.cluster-xyz.us-east-1.rds.amazonaws.com",
            "port": 5432,
            "database": "production"
        }

        return {
            "status": "success",
            "command": f"aws secretsmanager get-secret-value --secret-id {secret_name}",
            "output": {
                "ARN": f"arn:aws:secretsmanager:us-east-1:123456789012:secret:{secret_name}",
                "Name": secret_name,
                "SecretString": str(secret_value)
            },
            "stdout": str(secret_value),
            "execution_mode": "mock-realistic"
        }

    def _mock_aws_generic(self, target: str) -> Dict[str, any]:
        """Mock generic AWS command."""
        return {
            "status": "success",
            "command": target,
            "output": {"message": "AWS command executed"},
            "stdout": "Command completed successfully",
            "execution_mode": "mock-realistic"
        }

    def _mock_ssh(self, target: str) -> Dict[str, any]:
        """Generate mock SSH command outputs."""
        hostname = "prod-server-01"

        stdout = f"""Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-88-generic x86_64)

Last login: Tue Jan 28 10:15:32 2025 from 192.168.1.100

admin@{hostname}:~$ whoami
admin
admin@{hostname}:~$ hostname
{hostname}
admin@{hostname}:~$ uname -a
Linux {hostname} 5.15.0-88-generic #98-Ubuntu SMP x86_64 GNU/Linux
admin@{hostname}:~$ pwd
/home/admin
"""

        return {
            "status": "success",
            "command": f"ssh admin@{hostname}",
            "output": {"host": hostname, "user": "admin"},
            "stdout": stdout,
            "execution_mode": "mock-realistic"
        }

    def _mock_curl(self, target: str) -> Dict[str, any]:
        """Generate mock curl command outputs."""
        url = "https://api.internal.company.com/health"
        if "http" in target:
            parts = target.split()
            for part in parts:
                if part.startswith("http"):
                    url = part
                    break

        response_body = {
            "status": "healthy",
            "version": "1.2.3",
            "uptime": 864723,
            "services": {
                "database": "connected",
                "redis": "connected",
                "s3": "accessible"
            }
        }

        return {
            "status": "success",
            "command": f"curl {url}",
            "output": response_body,
            "stdout": str(response_body),
            "execution_mode": "mock-realistic"
        }

    def _mock_generic(self, target: str) -> Dict[str, any]:
        """Generate generic command output."""
        return {
            "status": "success",
            "command": target,
            "output": {"message": "Command executed in mock-realistic mode"},
            "stdout": f"Executed: {target}\nOutput: (simulated)",
            "execution_mode": "mock-realistic"
        }
