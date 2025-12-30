# ImagoMortis - Kubernetes Deployment

This directory contains the complete Kubernetes manifests to deploy the ImagoMortis application.


## Files Structure

| File | Description |
|------|-------------|
| `namespace.yaml` | Creates the `imagomortis` namespace |
| `configmap.yaml` | Configuration values for all services |
| `secrets.yaml` | Database credentials (update for production!) |
| `pvc.yaml` | Persistent Volume Claims for PostgreSQL and uploads |
| `postgres.yaml` | PostgreSQL StatefulSet and Service |
| `uploader.yaml` | Uploader Deployment and Service |
| `pusher.yaml` | Pusher Deployment |
| `api.yaml` | API Deployment and Service |
| `webui.yaml` | Web UI Deployment and Service |
| `ingress.yaml` | Ingress + NodePort services for external access |
| `kustomization.yaml` | Kustomize configuration for easy deployment |

## Prerequisites

1. A running Kubernetes cluster (minikube, kind, k3s, or cloud-managed)
2. `kubectl` configured to access your cluster
3. Docker images built and pushed to a registry (or locally available)
4. A StorageClass that supports `ReadWriteMany` (RWX) for the uploads PVC

## Building Docker Images

Before deploying, build and push the Docker images:

```bash
# From the project root directory
cd ..

# Build all images
docker build -t imagomortis/uploader:latest ./uploader
docker build -t imagomortis/pusher:latest ./pusher
docker build -t imagomortis/api:latest ./api
docker build -t imagomortis/webui:latest ./webui

# For a remote registry, tag and push:
# docker tag imagomortis/uploader:latest your-registry/imagomortis/uploader:latest
# docker push your-registry/imagomortis/uploader:latest
# (repeat for all images)
```

## Deployment Options

### Option 1: Using Kustomize (Recommended)

```bash
# Deploy everything
kubectl apply -k .

# Or preview what will be deployed
kubectl kustomize .
```

### Option 2: Manual Deployment

Apply the manifests in order:

```bash
# 1. Create namespace first
kubectl apply -f namespace.yaml

# 2. Apply configuration and secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# 3. Create persistent storage
kubectl apply -f pvc.yaml

# 4. Deploy PostgreSQL (wait for it to be ready)
kubectl apply -f postgres.yaml
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgres -n imagomortis --timeout=120s

# 5. Deploy backend services
kubectl apply -f uploader.yaml
kubectl apply -f pusher.yaml
kubectl apply -f api.yaml

# 6. Deploy frontend
kubectl apply -f webui.yaml

# 7. Create ingress and nodeport services
kubectl apply -f ingress.yaml
```

## Accessing the Application

### Using NodePort (Local Development)

After deployment, access the services via NodePort:

- **Web UI**: http://localhost:30080
- **API**: http://localhost:30081
- **Uploader**: http://localhost:30082

For minikube, use:
```bash
minikube service webui-nodeport -n imagomortis
```

### Using Ingress

1. Add to `/etc/hosts`:
   ```
   127.0.0.1 imagomortis.local
   ```

2. If using minikube, enable ingress:
   ```bash
   minikube addons enable ingress
   ```

3. Access at: http://imagomortis.local

## Configuration

### Updating Secrets (Production)

⚠️ **Important**: Change the default database credentials before deploying to production!

Edit `secrets.yaml` or create a sealed secret:
```yaml
stringData:
  POSTGRES_USER: "your-secure-username"
  POSTGRES_PASSWORD: "your-secure-password"
```

### Updating ConfigMap

Modify `configmap.yaml` to change:
- Image resize dimensions
- Polling intervals
- Service URLs
- Ports

### Customizing Images

Update `kustomization.yaml` to use your own registry:
```yaml
images:
  - name: imagomortis/uploader
    newName: your-registry/imagomortis/uploader
    newTag: v1.0.0
```

## Scaling

```bash
# Scale API replicas
kubectl scale deployment api -n imagomortis --replicas=3

# Scale Web UI replicas
kubectl scale deployment webui -n imagomortis --replicas=3

# Note: Pusher should remain at 1 replica to avoid duplicate processing
```

## Monitoring

```bash
# Check all pods
kubectl get pods -n imagomortis

# Check logs
kubectl logs -f deployment/uploader -n imagomortis
kubectl logs -f deployment/pusher -n imagomortis
kubectl logs -f deployment/api -n imagomortis
kubectl logs -f deployment/webui -n imagomortis

# Check events
kubectl get events -n imagomortis --sort-by='.lastTimestamp'
```

## Cleanup

```bash
# Delete all resources
kubectl delete -k .

# Or manually
kubectl delete namespace imagomortis
```

## Storage Considerations

The `uploads-pvc` requires a StorageClass that supports `ReadWriteMany` (RWX) access mode since both the uploader and pusher need access to the same files.

For local development:
- **minikube**: Use the default storage or hostPath
- **kind**: Consider using a local-path provisioner

For production:
- Use NFS, CephFS, Azure Files, or AWS EFS
- Set the appropriate `storageClassName` in `pvc.yaml`

## Troubleshooting

### Pods stuck in Pending

```bash
kubectl describe pod <pod-name> -n imagomortis
```

Common causes:
- PVC not bound (check StorageClass)
- Insufficient resources

### Database connection issues

```bash
# Check if PostgreSQL is running
kubectl get pods -l app.kubernetes.io/name=postgres -n imagomortis

# Check PostgreSQL logs
kubectl logs -f statefulset/postgres -n imagomortis
```

