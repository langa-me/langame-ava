gcloud beta run services describe langame-djinn --project langame-dev --platform managed --region us-central1 --format=yaml > service.yaml

gcloud beta run deploy langame-djinn --project langame-dev --platform managed --region us-central1