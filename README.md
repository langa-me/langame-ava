# langame-ava

## Prerequisites

- [ ] Helm, Kubernetes, Docker, Python etc.
- [ ] Setup Cloud Docker registry in Kubernetes and in local machine


## Artifact registry CI/CD

```bash
PROJECT_ID=$(gcloud config get-value project)

# create service account for pushing containers to gcr
# and deploying to cloud run
gcloud iam service-accounts create langame-ava \
  --display-name "langame-ava"

# Artifact Registry Administrator
# Cloud Build Service Account
# Service Account User
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:langame-ava@${PROJECT_ID}.iam.gserviceaccount.com \
  --role roles/artifactregistry.writer

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member serviceAccount:langame-ava@${PROJECT_ID}.iam.gserviceaccount.com \
  --role roles/cloudbuild.builds.builder

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member serviceAccount:langame-ava@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.serviceAccountUser

# get svc key
KEY_PATH="langame-ava-deployer.svc.prod.json"
gcloud iam service-accounts keys create ${KEY_PATH} \
  --iam-account=langame-ava@${PROJECT_ID}.iam.gserviceaccount.com
cat ${KEY_PATH}
```
