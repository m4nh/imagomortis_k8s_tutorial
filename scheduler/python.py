import os
import sys
import time
import uuid
import random
import tempfile
import shutil
import psycopg2
import json
import threading
from datetime import datetime
from pathlib import Path
from loguru import logger
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

# Configure Loguru
logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)

# Configuration
POLL_INTERVAL = int(os.getenv("SCHEDULER_POLL_INTERVAL", "5"))
NAMESPACE = os.getenv("SCHEDULER_NAMESPACE", "imagomortis")
IMAGE_TASK_IMAGE = os.getenv(
    "SCHEDULER_IMAGE_TASK_IMAGE", "imagomortis/imagetask:latest"
)

# Database Configuration
DB_HOST = os.getenv("SCHEDULER_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
DB_PORT = os.getenv("SCHEDULER_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("SCHEDULER_DB_NAME", os.getenv("POSTGRES_DB", "imagomortis"))
DB_USER = os.getenv("SCHEDULER_DB_USER", os.getenv("POSTGRES_USER", "postgres"))
DB_PASSWORD = os.getenv(
    "SCHEDULER_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "postgres")
)

# Shared volume path (mounted in both scheduler and jobs)
SHARED_VOLUME_PATH = os.getenv("SCHEDULER_SHARED_VOLUME_PATH", "/app/shared")


def get_db_connection():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )


def init_k8s():
    """Initialize Kubernetes client."""
    try:
        # Try in-cluster config first (when running inside K8s)
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except config.ConfigException:
        # Fall back to kubeconfig (for local development)
        try:
            config.load_kube_config()
            logger.info("Loaded kubeconfig from default location")
        except config.ConfigException as e:
            logger.error(f"Failed to load Kubernetes config: {e}")
            sys.exit(1)


def get_pod_for_job(job_name: str, timeout: int = 30):
    """Return the first pod name for the given Job, waiting up to timeout seconds for it to start running/finish."""
    core_v1 = client.CoreV1Api()
    selector = f"job-name={job_name}"
    end = time.time() + timeout

    while time.time() < end:
        try:
            pods = core_v1.list_namespaced_pod(
                namespace=NAMESPACE, label_selector=selector
            )
        except Exception as e:
            logger.warning("Failed to list pods for job", job=job_name, error=str(e))
            time.sleep(1)
            continue

        if not pods.items:
            time.sleep(1)
            continue

        # Prefer a pod that is Running, Succeeded or Failed
        for pod in pods.items:
            phase = (pod.status.phase or "").capitalize()
            if phase in {"Running", "Succeeded", "Failed"}:
                return pod.metadata.name

        # If we have pods but none are ready yet, keep waiting
        logger.debug(
            "Pod exists but not ready yet",
            job=job_name,
            pods=[p.metadata.name for p in pods.items],
        )
        time.sleep(1)

    return None


def stream_pod_logs_and_report_progress(
    pod_name: str,
    container: str = "imagetask",
    on_progress=None,
    stop_event: threading.Event = None,
    wait_timeout: int = 60,
):
    """
    Stream logs from the given pod, parse JSON loguru lines, and invoke on_progress(progress, payload).
    Waits for the container to be Running/Terminated before attempting to stream logs and retries
    gracefully if the API responds with a "container is waiting to start" 400.
    """
    core_v1 = client.CoreV1Api()
    w = watch.Watch()

    def _container_ready(pname):
        end = time.time() + wait_timeout
        while time.time() < end:
            try:
                pod = core_v1.read_namespaced_pod(name=pname, namespace=NAMESPACE)
            except ApiException as e:
                logger.debug(
                    "Failed to read pod status while waiting for container",
                    pod=pname,
                    error=str(e),
                )
                time.sleep(1)
                continue
            except Exception as e:
                logger.debug("Unexpected error reading pod", pod=pname, error=str(e))
                time.sleep(1)
                continue

            statuses = pod.status.container_statuses or []
            for st in statuses:
                if st.name != container:
                    continue
                # If container is running or has terminated, we can read logs
                if (
                    getattr(st.state, "running", None) is not None
                    or getattr(st.state, "terminated", None) is not None
                ):
                    return True
                # If waiting, log the reason (useful for diagnostics)
                if getattr(st.state, "waiting", None) is not None:
                    reason = (
                        st.state.waiting.reason
                        if st.state.waiting.reason
                        else "waiting"
                    )
                    logger.debug(
                        "Container waiting",
                        pod=pname,
                        container=container,
                        reason=reason,
                    )
            time.sleep(1)
        return False

    # Wait for container readiness before attempting to stream logs
    ready = _container_ready(pod_name)
    if not ready:
        logger.info(
            "Container not ready to stream logs; will still attempt streaming with retries",
            pod=pod_name,
            container=container,
        )

    # Try streaming, but tolerate transient 400 "ContainerCreating" errors by retrying.
    retry_delay = 1
    max_retries = max(3, int(wait_timeout / 5))
    attempt = 0

    try:
        while not (stop_event and stop_event.is_set()):
            try:
                for line in w.stream(
                    core_v1.read_namespaced_pod_log,
                    name=pod_name,
                    namespace=NAMESPACE,
                    container=container,
                    follow=True,
                    _preload_content=False,
                    tail_lines=10,
                ):
                    if stop_event and stop_event.is_set():
                        w.stop()
                        break

                    try:
                        raw_line = (
                            line.decode("utf-8", errors="replace")
                            if isinstance(line, (bytes, bytearray))
                            else str(line)
                        ).strip()
                        if not raw_line:
                            continue

                        try:
                            payload = json.loads(raw_line)
                        except Exception:
                            # Not JSON; skip
                            continue

                        progress = (
                            payload.get("record", {})
                            .get("extra", {})
                            .get("progress", {})
                        )

                        logger.debug(
                            "Pod log line",
                            pod=pod_name,
                            line=raw_line,
                            progress=progress,
                        )

                        if progress and on_progress:
                            try:
                                on_progress(progress)
                            except Exception as callback_err:
                                logger.warning(
                                    "Progress callback failed",
                                    pod=pod_name,
                                    error=str(callback_err),
                                )
                    except Exception:
                        logger.error(
                            "Failed to parse log line", pod=pod_name, line=raw_line
                        )
                        continue

                # If we've exited the inner for-loop normally, break out (no more streaming)
                break

            except ApiException as api_err:
                msg = str(api_err)
                attempt += 1
                # If container is still creating, the API returns 400; retry a few times
                if getattr(api_err, "status", None) == 400 and (
                    "ContainerCreating" in msg or "is waiting to start" in msg
                ):
                    logger.debug(
                        "Container not ready for logs (API 400); retrying",
                        pod=pod_name,
                        attempt=attempt,
                        error=msg,
                    )
                    if stop_event and stop_event.is_set():
                        break
                    if attempt >= max_retries:
                        logger.warning(
                            "Exceeded log-stream retries for pod", pod=pod_name
                        )
                        break
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 5)
                    continue
                else:
                    logger.warning(
                        "Log streaming stopped with ApiException",
                        pod=pod_name,
                        error=msg,
                    )
                    break
            except Exception as stream_err:
                logger.warning(
                    "Log streaming stopped", pod=pod_name, error=str(stream_err)
                )
                break
    finally:
        try:
            w.stop()
        except Exception:
            pass


def update_image_job_progress(image_id: str, job_id: str, progress, payload=None):
    """Persist progress into the job column for visibility."""
    conn = get_db_connection()
    cur = conn.cursor()

    job_status = {
        "acquired": True,
        "job_id": job_id,
        "progress": progress,
        "last_progress_at": datetime.utcnow().isoformat(),
    }
    if payload:
        job_status["last_progress_payload"] = payload

    try:
        cur.execute(
            """
            UPDATE images
            SET job = %s
            WHERE id = %s
            """,
            (json.dumps(job_status), image_id),
        )
        conn.commit()
        logger.info(f"Updated image job progress", image_id=image_id, progress=progress)
    except Exception as e:
        conn.rollback()
        logger.warning(f"Failed to update progress: {e}", image_id=image_id)
    finally:
        cur.close()
        conn.close()


def acquire_image_job():
    """
    Atomically acquire an image that needs processing.
    Uses FOR UPDATE SKIP LOCKED for safe concurrent access by multiple schedulers.
    Returns (image_id, image_data) or (None, None) if no work available.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Start transaction
        cur.execute("BEGIN")

        # Find and lock one image with NULL job, skipping locked rows
        cur.execute(
            """
            SELECT id, data FROM images
            WHERE job IS NULL
            ORDER BY RANDOM()
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )
        row = cur.fetchone()

        if row is None:
            conn.rollback()
            return None, None

        image_id, image_data = row
        job_id = str(uuid.uuid4())

        # Atomically mark as acquired
        cur.execute(
            """
            UPDATE images
            SET job = %s
            WHERE id = %s
            """,
            (
                f'{{"acquired": true, "job_id": "{job_id}", "started_at": "{datetime.utcnow().isoformat()}"}}',
                image_id,
            ),
        )
        conn.commit()

        logger.info(
            f"Acquired image for processing", image_id=str(image_id), job_id=job_id
        )
        return str(image_id), image_data, job_id

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to acquire image job: {e}")
        return None, None, None
    finally:
        cur.close()
        conn.close()


def create_k8s_job(image_id: str, job_id: str, input_path: str, output_path: str):
    """
    Create a Kubernetes Job to process the image.
    """
    batch_v1 = client.BatchV1Api()

    job_name = f"imagetask-{job_id[:8]}"

    # Container specification
    container = client.V1Container(
        name="imagetask",
        image=IMAGE_TASK_IMAGE,
        image_pull_policy="IfNotPresent",
        args=[
            f"--input-path={input_path}",
            f"--output-path={output_path}",
        ],
        volume_mounts=[
            client.V1VolumeMount(
                name="shared-data",
                mount_path="/app/shared",
            )
        ],
    )

    # Pod template
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={
                "app.kubernetes.io/name": "imagetask",
                "app.kubernetes.io/component": "worker",
                "app.kubernetes.io/part-of": "imagomortis",
                "imagomortis/image-id": image_id[:8],
                "imagomortis/job-id": job_id[:8],
            }
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[
                client.V1Volume(
                    name="shared-data",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name="scheduler-shared-pvc"
                    ),
                )
            ],
        ),
    )

    # Job specification
    job_spec = client.V1JobSpec(
        template=template,
        backoff_limit=0,  # Don't retry on failure
        ttl_seconds_after_finished=300,  # Cleanup after 5 minutes if we miss it
    )

    # Job object
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            namespace=NAMESPACE,
            labels={
                "app.kubernetes.io/name": "imagetask",
                "app.kubernetes.io/component": "worker",
                "app.kubernetes.io/part-of": "imagomortis",
                "app.kubernetes.io/managed-by": "scheduler",
            },
        ),
        spec=job_spec,
    )

    try:
        batch_v1.create_namespaced_job(namespace=NAMESPACE, body=job)
        logger.info(f"Created Kubernetes Job", job_name=job_name, image_id=image_id)
        return job_name
    except ApiException as e:
        logger.error(f"Failed to create Kubernetes Job: {e}")
        raise


def wait_for_job_completion(job_name: str, image_id: str = None, job_id: str = None):
    """
    Wait for a Kubernetes Job to complete (success or failure) while streaming progress logs.
    Returns True if succeeded, False if failed.
    """
    batch_v1 = client.BatchV1Api()

    logger.info(f"Waiting for job completion", job_name=job_name)

    # Try to locate the pod and stream progress logs in the background
    pod_name = get_pod_for_job(job_name)
    stop_event = threading.Event()
    stream_thread = None

    if pod_name:

        def _on_progress(progress_dict):
            logger.info(
                "Progress update",
                job_name=job_name,
                pod=pod_name,
                progress=progress_dict,
            )
            logger.warning(
                "Updating image job progress", image_id=image_id, job_id=job_id
            )
            if image_id and job_id:
                update_image_job_progress(image_id, job_id, progress_dict)

        stream_thread = threading.Thread(
            target=stream_pod_logs_and_report_progress,
            args=(pod_name,),
            kwargs={"on_progress": _on_progress, "stop_event": stop_event},
            daemon=True,
        )
        stream_thread.start()
    else:
        logger.info("Pod not found for job; skipping log streaming", job_name=job_name)

    try:
        while True:
            try:
                job = batch_v1.read_namespaced_job(name=job_name, namespace=NAMESPACE)

                if job.status.succeeded is not None and job.status.succeeded > 0:
                    logger.info(f"Job completed successfully", job_name=job_name)
                    return True

                if job.status.failed is not None and job.status.failed > 0:
                    logger.warning(f"Job failed", job_name=job_name)
                    return False

                # Still running, wait and poll again
                time.sleep(2)

            except ApiException as e:
                logger.error(f"Failed to check job status: {e}", job_name=job_name)
                return False
    finally:
        stop_event.set()
        if stream_thread:
            stream_thread.join(timeout=5)


def delete_k8s_job(job_name: str):
    """
    Delete a Kubernetes Job and its pods.
    """
    batch_v1 = client.BatchV1Api()

    try:
        batch_v1.delete_namespaced_job(
            name=job_name,
            namespace=NAMESPACE,
            body=client.V1DeleteOptions(
                propagation_policy="Foreground"  # Delete pods too
            ),
        )
        logger.info(f"Deleted Kubernetes Job", job_name=job_name)
    except ApiException as e:
        if e.status == 404:
            logger.warning(f"Job already deleted", job_name=job_name)
        else:
            logger.error(f"Failed to delete job: {e}", job_name=job_name)


def update_image_job_status(
    image_id: str,
    job_id: str,
    success: bool,
    output_data: bytes = None,
    error: str = None,
):
    """
    Update the image's job status in the database.
    If successful and output_data is provided, update the image data.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        if success and output_data:
            # Update with new processed image data
            job_status = f'{{"completed": true, "job_id": "{job_id}", "completed_at": "{datetime.utcnow().isoformat()}"}}'
            cur.execute(
                """
                UPDATE images
                SET data = %s, job = %s
                WHERE id = %s
                """,
                (output_data, job_status, image_id),
            )
            logger.info(f"Updated image with processed data", image_id=image_id)
        else:
            # Mark as failed
            error_msg = error.replace('"', '\\"') if error else "Unknown error"
            job_status = f'{{"failed": true, "job_id": "{job_id}", "failed_at": "{datetime.utcnow().isoformat()}", "error": "{error_msg}"}}'
            cur.execute(
                """
                UPDATE images
                SET job = %s
                WHERE id = %s
                """,
                (job_status, image_id),
            )
            logger.warning(
                f"Marked image job as failed", image_id=image_id, error=error
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to update image job status: {e}", image_id=image_id)
    finally:
        cur.close()
        conn.close()


def process_image(image_id: str, image_data: bytes, job_id: str):
    """
    Process a single image:
    1. Save image to shared volume
    2. Create K8s Job
    3. Wait for completion
    4. Read output and update DB
    5. Cleanup
    """
    # Ensure shared volume directory exists
    shared_path = Path(SHARED_VOLUME_PATH)
    shared_path.mkdir(parents=True, exist_ok=True)

    # Create unique input/output paths
    input_filename = f"{job_id}-input.jpg"
    output_filename = f"{job_id}-output.jpg"
    input_path = shared_path / input_filename
    output_path = shared_path / output_filename

    # Paths as seen from inside the K8s Job container
    container_input_path = f"/app/shared/{input_filename}"
    container_output_path = f"/app/shared/{output_filename}"

    job_name = None

    try:
        # 1. Write input image to shared volume
        with open(input_path, "wb") as f:
            f.write(image_data)
        logger.info(
            f"Wrote input image to shared volume",
            path=str(input_path),
            image_id=image_id,
        )

        # 2. Create K8s Job
        job_name = create_k8s_job(
            image_id, job_id, container_input_path, container_output_path
        )

        # 3. Wait for job completion (while streaming progress)
        success = wait_for_job_completion(job_name, image_id=image_id, job_id=job_id)

        if success:
            # 4. Read output image
            if output_path.exists():
                with open(output_path, "rb") as f:
                    output_data = f.read()

                # Update DB with processed image
                update_image_job_status(
                    image_id, job_id, success=True, output_data=output_data
                )
            else:
                logger.error(
                    f"Output file not found", path=str(output_path), image_id=image_id
                )
                update_image_job_status(
                    image_id, job_id, success=False, error="Output file not found"
                )
        else:
            update_image_job_status(image_id, job_id, success=False, error="Job failed")

        # 5. Delete K8s Job
        if job_name:
            delete_k8s_job(job_name)

    except Exception as e:
        logger.error(f"Error processing image: {e}", image_id=image_id)
        update_image_job_status(image_id, job_id, success=False, error=str(e))

        # Try to delete job if it was created
        if job_name:
            try:
                delete_k8s_job(job_name)
            except Exception:
                pass

    finally:
        # Cleanup temp files
        try:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup temp files: {e}")


def main():
    logger.info("Scheduler service starting up")

    # Initialize Kubernetes client
    init_k8s()

    # Ensure shared volume path exists
    shared_path = Path(SHARED_VOLUME_PATH)
    if not shared_path.exists():
        logger.info(f"Creating shared volume path: {SHARED_VOLUME_PATH}")
        shared_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Scheduler ready, polling every {POLL_INTERVAL}s")

    while True:
        try:
            # Try to acquire an image job
            result = acquire_image_job()

            if result[0] is not None:
                image_id, image_data, job_id = result
                process_image(image_id, image_data, job_id)
            else:
                # No work available, sleep before next poll
                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Stopping scheduler service")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
