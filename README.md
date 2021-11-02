```bash
conda install --file requirements.txt
```


```bash
IMAGE_TAG=gcr.io/langame-dev/langame-ava
gcloud builds submit --tag "$IMAGE_TAG" . --timeout 20m --project langame-dev

gcloud config set app/cloud_build_timeout 1000
gcloud run deploy langame-ava --project langame-dev --region europe-west3 --tag "$IMAGE_TAG" --source . --allow-unauthenticated
```