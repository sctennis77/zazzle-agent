"""
Kubernetes Job Manager for on-demand task processing.

This module handles creating and managing Kubernetes Jobs for commission tasks.
It provides a modern, scalable alternative to the database queue system.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config import kube_config

from app.db.models import Donation
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class K8sJobManager:
    """
    Manages Kubernetes Jobs for commission task processing.

    This class handles:
    - Creating K8s Jobs for commission tasks
    - Monitoring job status
    - Updating task progress
    - Cleanup of completed jobs
    """

    def __init__(self, namespace: str = "zazzle-agent"):
        """
        Initialize the K8s Job Manager.

        Args:
            namespace: Kubernetes namespace for jobs
        """
        self.namespace = namespace

        # Load kubeconfig (works for both local and cluster)
        try:
            config.load_incluster_config()  # Try in-cluster config first
            logger.info("Using in-cluster Kubernetes configuration")
        except config.ConfigException:
            try:
                config.load_kube_config()  # Fallback to local kubeconfig
                logger.info("Using local Kubernetes configuration")
            except config.ConfigException:
                logger.warning("No Kubernetes configuration found - K8s Jobs disabled")
                self.enabled = False
                return

        self.enabled = True
        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()

        logger.info(f"K8s Job Manager initialized for namespace: {namespace}")

    def create_commission_job(
        self, donation: Donation, task_data: Dict[str, Any]
    ) -> Optional[str]:
        """
        Create a Kubernetes Job for commission processing.

        Args:
            donation: The donation that triggered the commission
            task_data: Task configuration data

        Returns:
            Job name if created successfully, None otherwise
        """
        if not self.enabled:
            logger.warning("K8s Jobs disabled - falling back to database queue")
            return None

        try:
            job_name = (
                f"commission-{donation.id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )

            # Create job manifest
            job_manifest = self._create_job_manifest(
                job_name=job_name, donation_id=donation.id, task_data=task_data
            )

            # Create the job
            api_response = self.batch_v1.create_namespaced_job(
                body=job_manifest, namespace=self.namespace
            )

            logger.info(f"Created K8s Job: {job_name}")
            return job_name

        except ApiException as e:
            logger.error(f"Failed to create K8s Job: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating K8s Job: {e}")
            return None

    def get_job_status(self, job_name: str) -> Dict[str, Any]:
        """
        Get the status of a Kubernetes Job.

        Args:
            job_name: Name of the job

        Returns:
            Dictionary with job status information
        """
        if not self.enabled:
            return {"status": "disabled", "error": "K8s Jobs not enabled"}

        try:
            job = self.batch_v1.read_namespaced_job(
                name=job_name, namespace=self.namespace
            )

            status = {
                "name": job_name,
                "status": "Unknown",
                "start_time": None,
                "completion_time": None,
                "succeeded": 0,
                "failed": 0,
                "active": 0,
                "ready": 0,
                "pods": [],
            }

            if job.status:
                if job.status.succeeded:
                    status["status"] = "Succeeded"
                    status["succeeded"] = job.status.succeeded
                elif job.status.failed:
                    status["status"] = "Failed"
                    status["failed"] = job.status.failed
                elif job.status.active:
                    status["status"] = "Running"
                    status["active"] = job.status.active
                elif job.status.ready:
                    status["status"] = "Ready"
                    status["ready"] = job.status.ready

                if job.status.start_time:
                    status["start_time"] = job.status.start_time.isoformat()
                if job.status.completion_time:
                    status["completion_time"] = job.status.completion_time.isoformat()

            # Get pod information
            pods = self._get_job_pods(job_name)
            status["pods"] = pods

            return status

        except ApiException as e:
            if e.status == 404:
                return {"status": "NotFound", "error": f"Job {job_name} not found"}
            logger.error(f"Failed to get job status: {e}")
            return {"status": "Error", "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error getting job status: {e}")
            return {"status": "Error", "error": str(e)}

    def list_jobs(self, label_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all commission jobs.

        Args:
            label_selector: Optional label selector for filtering

        Returns:
            List of job status dictionaries
        """
        if not self.enabled:
            return []

        try:
            jobs = self.batch_v1.list_namespaced_job(
                namespace=self.namespace,
                label_selector=label_selector or "app=zazzle-commission",
            )

            job_list = []
            for job in jobs.items:
                job_status = self.get_job_status(job.metadata.name)
                job_list.append(job_status)

            return job_list

        except ApiException as e:
            logger.error(f"Failed to list jobs: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing jobs: {e}")
            return []

    def delete_job(self, job_name: str) -> bool:
        """
        Delete a completed job.

        Args:
            job_name: Name of the job to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.batch_v1.delete_namespaced_job(name=job_name, namespace=self.namespace)
            logger.info(f"Deleted K8s Job: {job_name}")
            return True

        except ApiException as e:
            logger.error(f"Failed to delete job {job_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting job {job_name}: {e}")
            return False

    def _create_job_manifest(
        self, job_name: str, donation_id: int, task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create the Kubernetes Job manifest.

        Args:
            job_name: Name for the job
            donation_id: ID of the donation
            task_data: Task configuration data

        Returns:
            Job manifest dictionary
        """
        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": self.namespace,
                "labels": {
                    "app": "zazzle-commission",
                    "donation-id": str(donation_id),
                    "type": "commission-task",
                },
            },
            "spec": {
                "backoffLimit": 3,
                "ttlSecondsAfterFinished": 3600,  # Clean up after 1 hour
                "template": {
                    "metadata": {
                        "labels": {
                            "app": "zazzle-commission",
                            "donation-id": str(donation_id),
                        }
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "containers": [
                            {
                                "name": "commission-worker",
                                "image": "zazzle-agent:latest",  # Use your image
                                "command": ["python", "-m", "app.commission_worker"],
                                "args": [
                                    "--donation-id",
                                    str(donation_id),
                                    "--task-data",
                                    json.dumps(task_data),
                                ],
                                "env": [
                                    {"name": "DONATION_ID", "value": str(donation_id)},
                                    {
                                        "name": "TASK_DATA",
                                        "value": json.dumps(task_data),
                                    },
                                ],
                                "resources": {
                                    "requests": {"memory": "512Mi", "cpu": "250m"},
                                    "limits": {"memory": "1Gi", "cpu": "500m"},
                                },
                            }
                        ],
                    },
                },
            },
        }

    def _get_job_pods(self, job_name: str) -> List[Dict[str, Any]]:
        """
        Get pod information for a job.

        Args:
            job_name: Name of the job

        Returns:
            List of pod status dictionaries
        """
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"job-name={job_name}"
            )

            pod_list = []
            for pod in pods.items:
                pod_info = {
                    "name": pod.metadata.name,
                    "status": pod.status.phase if pod.status else "Unknown",
                    "ready": False,
                    "restart_count": 0,
                }

                if pod.status:
                    if pod.status.container_statuses:
                        container_status = pod.status.container_statuses[0]
                        pod_info["ready"] = container_status.ready
                        pod_info["restart_count"] = container_status.restart_count

                pod_list.append(pod_info)

            return pod_list

        except ApiException as e:
            logger.error(f"Failed to get pods for job {job_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting pods for job {job_name}: {e}")
            return []
