# ImagoMortis Helm Chart

A Helm chart for deploying ImagoMortis - an image processing application with upload, processing, and viewing capabilities.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (for persistence)
- StorageClass with `ReadWriteMany` support (for shared volumes)

## Installation

### Add the repository (if published)

```bash
helm repo add imagomortis https://your-helm-repo.com
helm repo update
```

### Install from local chart

```bash
cd helm
helm install imagomortis ./imagomortis -n imagomortis --create-namespace
```

### Install with custom values

```bash
helm install imagomortis ./imagomortis -n imagomortis --create-namespace -f values-production.yaml
```

## Configuration

The following table lists the configurable parameters and their default values.

### Global Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imagePullPolicy` | Global image pull policy | `IfNotPresent` |
| `global.storageClass` | Global storage class | `""` |
| `namespace.create` | Create namespace | `true` |
| `namespace.name` | Namespace name | `imagomortis` |

### Database Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Deploy built-in PostgreSQL | `true` |
| `postgresql.auth.username` | PostgreSQL username | `postgres` |
| `postgresql.auth.password` | PostgreSQL password | `postgres` |
| `postgresql.auth.database` | PostgreSQL database | `imagomortis` |
| `postgresql.primary.persistence.size` | Storage size | `5Gi` |

### Components

Each component (uploader, pusher, api, webui, scheduler) has the following configurable parameters:

| Parameter | Description |
|-----------|-------------|
| `<component>.enabled` | Enable the component |
| `<component>.replicaCount` | Number of replicas |
| `<component>.image.repository` | Image repository |
| `<component>.image.tag` | Image tag |
| `<component>.resources` | CPU/Memory resource requests/limits |

### Ingress

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `""` |
| `ingress.host` | Ingress hostname | `imagomortis.local` |
| `ingress.tls` | TLS configuration | `[]` |

### NodePort (Development)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `nodePort.enabled` | Enable NodePort services | `true` |
| `nodePort.webui.port` | WebUI NodePort | `30080` |
| `nodePort.api.port` | API NodePort | `30081` |
| `nodePort.uploader.port` | Uploader NodePort | `30082` |

### Logging Stack

| Parameter | Description | Default |
|-----------|-------------|---------|
| `logging.enabled` | Enable logging stack | `true` |
| `logging.loki.persistence.size` | Loki storage size | `10Gi` |
| `logging.grafana.enabled` | Enable Grafana | `true` |
| `logging.fluentBit.enabled` | Enable Fluent Bit | `true` |

## Examples

### Production deployment with Ingress

```yaml
# values-production.yaml
namespace:
  name: imagomortis-prod

postgresql:
  auth:
    password: "your-secure-password"
  primary:
    persistence:
      size: 20Gi

ingress:
  enabled: true
  className: nginx
  host: imagomortis.example.com
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
  tls:
    - secretName: imagomortis-tls
      hosts:
        - imagomortis.example.com

nodePort:
  enabled: false

webui:
  config:
    publicUploadServiceUrl: "https://imagomortis.example.com/upload"
    publicApiServiceUrl: "https://imagomortis.example.com/api"
    origin: "https://imagomortis.example.com"
```

### Local development

```yaml
# values-local.yaml
ingress:
  enabled: false

nodePort:
  enabled: true
  webui:
    port: 30080
  api:
    port: 30081
  uploader:
    port: 30082

logging:
  grafana:
    service:
      type: NodePort
```

## Upgrading

```bash
helm upgrade imagomortis ./imagomortis -n imagomortis -f values.yaml
```

## Uninstalling

```bash
helm uninstall imagomortis -n imagomortis
```

**Note:** This will not delete PersistentVolumeClaims. To fully clean up:

```bash
kubectl delete pvc -l app.kubernetes.io/instance=imagomortis -n imagomortis
kubectl delete namespace imagomortis
```

## Architecture

The chart deploys the following components:

- **PostgreSQL**: Database for storing image metadata
- **Uploader**: Receives and resizes uploaded images
- **Pusher**: Processes uploaded images and stores metadata in the database
- **API**: REST API for querying image data
- **WebUI**: SvelteKit-based web interface
- **Scheduler**: Creates Kubernetes Jobs for background image processing
- **Logging Stack**: Loki + Grafana + Fluent Bit for centralized logging
