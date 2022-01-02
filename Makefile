REGISTRY ?= gcr.io/$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)/ava
VERSION ?= latest
OPENAI_KEY ?= $(shell cat .env | grep OPENAI_KEY | cut -d '=' -f 2)
OPENAI_ORG ?= $(shell cat .env | grep OPENAI_ORG | cut -d '=' -f 2)
HUGGINGFACE_TOKEN ?= $(shell cat .env | grep HUGGINGFACE_TOKEN | cut -d '=' -f 2)
HUGGINGFACE_KEY ?= $(shell cat .env | grep HUGGINGFACE_KEY | cut -d '=' -f 2)
SVC_DEV_PATH ?= "./svc.dev.json"
SVC_PROD_PATH ?= "./svc.prod.json"
GCLOUD_PROJECT:=$(shell gcloud config list --format 'value(core.project)' 2>/dev/null)

gcloud_prod: ## Set the GCP project to prod
	gcloud config set project langame-86ac4

gcloud_dev: ## Set the GCP project to dev
	gcloud config set project langame-dev

# eval $(cat .env | sed 's/^/export /')

# docker

docker_build: ## [Local development] build the docker image
	mkdir -p third_party/langame-worker/langame
	cp -r ../langame-worker/langame/ third_party/langame-worker/
	cp ../langame-worker/setup.py third_party/langame-worker/setup.py
	docker build -t ${REGISTRY}:${VERSION} . -f ./Dockerfile --build-arg HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
	rm -rf third_party

docker_run: docker_build ## [Local development] run the docker container
	docker run \
		-v $(shell pwd)/svc.dev.json:/etc/secrets/primary/svc.json \
		-e OPENAI_KEY=${OPENAI_KEY} \
		-e OPENAI_ORG=${OPENAI_ORG} \
		-e HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN} \
		-e HUGGINGFACE_KEY=${HUGGINGFACE_KEY} \
		${REGISTRY}:${VERSION} --fix_grammar False --profanity_threshold tolerant --completion_type openai_api --tweet_on_generate True

docker_push: docker_build ## [Local development] push the docker image to GCR
	docker push ${REGISTRY}:${VERSION}

# k8s

k8s_dev_deploy: ## [Local development] deploy to Kubernetes.
	helm install ava helm -f helm/values-dev.yaml -n ava-dev --create-namespace
k8s_prod_deploy: ## [Local development] deploy to Kubernetes.
	helm install ava helm -f helm/values-prod.yaml -n ava-prod --create-namespace
k8s_dev_upgrade: ## [Local development] upgrade with new config.
	helm upgrade ava helm -f helm/values-dev.yaml -n ava-dev --recreate-pods
k8s_prod_upgrade: ## [Local development] upgrade with new config.
	helm upgrade ava helm -f helm/values-prod.yaml -n ava-prod --recreate-pods
k8s_dev_undeploy: ## [Local development] undeploy from Kubernetes.
	helm uninstall ava -n ava-dev
k8s_prod_undeploy: ## [Local development] undeploy from Kubernetes.
	helm uninstall ava -n ava-prod

# baremetal

protos: ## [Local development] Generate protos.
	python3 -m grpc_tools.protoc \
		--python_out=. \
		--include_imports \
		--include_source_info \
		proto/ava/v1/*.proto

install: ## [Local development] Upgrade pip, install requirements, install package.
	(\
		python3 -m virtualenv env; \
		. env/bin/activate; \
		python3 -m pip install -U pip; \
		python3 -m pip install -e .; \
		python3 -m pip install -r requirements-test.txt; \
	)

lint: ## [Local development] Run pylint to check code style.
	@echo "Linting krafla"
	env/bin/python3 -m pylint ava

run: ## [Local development] run the main entrypoint
	python3 $(shell pwd)/ava/main.py --service_account_key_path=svc.prod.json \
		--fix_grammar False \
		--profanity_threshold tolerant \
		--completion_type openai_api


.PHONY: help

help: # Run `make help` to get help on the make commands
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# apiVersion: v1
# kind: Secret
# metadata:
#   name: google-cloud-service-account
# data:
#   .dockerconfigjson: >-
#		{"auths":{"asia.gcr.io":{"username":"_json_key","password":"{{ .Files.Get .Values.googleCloud.containerRegistryServiceAccount | indent 4 }}
# type: kubernetes.io/dockerconfigjson

# {"auths":{"asia.gcr.io":{"username":"_json_key",
# {"auths":{"https://gcr.io":{"username":"_json_key","password":"{\n  \"type\": \"service_account\",\n  \"project_id\": \"langame-dev\",\n  \"private_key_id\": \"c477c960e8c3a1b3a8ca762f097a1990594d058c\",\n  \"private_key\": \"-----BEGIN PRIVATE KEY-----\\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC9OV8e+mLW4oJm\\nqfOthmy0+EvNImKTJFw87CL/9LcmmYN8+kF/mpjPjFcwZGY8OXK51UelXR91Vz0V\\n5UnO9Lm90MDXjZJgLTn7Yk+rsDNQRM5e19c4UUe1SSXIU4e1PlMu0z4HJVc1jxvc\\nkmW5xGN136ZGX08HNFsaKQ3QsLxZ3rFbskATwCMiC1/SIFdANfGxf2MbgwKu0Hw0\\nyO57wEIiBkQeBDzg0S8j0KIzdgS6uI0jrt38YysweyvNjSmX/kTLbaW16e9bygiL\\n/okdsEIGBtZE+b3avAZEvgX4Y2XmNPbuJombcr4jtqpoHLoE92RIujsJ8MtaRvCA\\ncbec+u1PAgMBAAECggEAQKOeElN/Ox+yYwawdrkCXompP0B9Qv17QtZ5mE0M2bM8\\nPw+wGzqA8/lheWb6o50OS1wHtv4KNofgFqA2Z+uinax3i8rRU2hvs6egRqqQxN1U\\nUALUgukFIXEE5pteMvRA7zB7Mm63jVS/NEiQVna3cTc+sjBxqyjf7B5VGVKebOY2\\nG1gDI2krEg8qIO/eDqs6poBLGsIMujeEJAou2Q53f5ih0fVACRE7m2RMd6IBzaUm\\n821Ky/eYinGJx8EcIOwGmdc3SV+EJJ7ORmj9KgkxkFWLmgkPUdF67fEZfGZvjWD+\\nkwgHHMPDiOphL2SoNxgP1TsZOLEEDKTEFwJnZEvWyQKBgQD1Ev4LVBylEq45D7HV\\nBwyQop6NOYDlCOFcCCWGGe6Hzwf3gYI3ygwx11HfZiW0ySd+XaSmO7nFthM1jTN5\\nkkibpskRX7dFKxQAKH49EHlgMD420x5m9zcFTBo5oFclHGyIOefXnTv631HeJ91m\\nfCCR6p0xjcS4yUqEhHtgkcJQaQKBgQDFqPe8QO+Ur+tatRNgvcfrzS3sSf73NN+5\\ndBvZAJEtSOaIXRmrmGp5XdrAQ6SVOHVH9vBPMPcxqnpND+s6L0v5EESU4Px2g6Bh\\nwwUf6B2Er4bcdHwoEdm9W3XaeMl6rgYoqinwb5q0380rUuHmyQatiETn0qzDspnm\\nvDw/rJmY9wKBgDVQUWXDgYvDmZUePfB63Rfl2JoeZVTt7qCnwQoAQCzZNAF68goS\\n8T4yekQgI5nFnMrXskbbfVlud5VRx13uHc+Go/0clnD8oxg5tuSv3ce4FwC0Qsvh\\ngd2sJZRdtjeDjHTCLBZyxSaZSGUMxRRTcn5rzJCIJ8CPQZ+8dl6Wtu/pAoGAZERj\\nb1bNcfKPhFMIwnFjIgXSPuQGd6aVuwDgQ4NbIcqyTwhTRk2p7Wkj15Y4vg2GyPvG\\nSZXAP6yIH+FsZParJmwPLiq3RvNcf1srlVTs7GsSEXDxrm3ns3va2/mb0yTGMQio\\n/7PNmeVRsaF4wNbHEW5n7eVcCGXoVji0o2ROAl8CgYB1NbNSP+8kLf/X9aXj/vEC\\nSjjbtI7oxuHsyme39oCXuDLprnFPtFM3YW3tcIUp25Af86v1kj2mIm+cTVY2Aaj/\\nu9M6UyJtV5tXfDEOyJ4/tGH0ty7ArkbxPLdiKAvSUMmOZLlraXdDUeaL2q7H6Aah\\n/S8+yBk2yY2EUbnK1p60zw==\\n-----END PRIVATE KEY-----\\n\",\n  \"client_email\": \"k8s-gcr-auth-ro@langame-dev.iam.gserviceaccount.com\",\n  \"client_id\": \"113483711361271620974\",\n  \"auth_uri\": \"https://accounts.google.com/o/oauth2/auth\",\n  \"token_uri\": \"https://oauth2.googleapis.com/token\",\n  \"auth_provider_x509_cert_url\": \"https://www.googleapis.com/oauth2/v1/certs\",\n  \"client_x509_cert_url\": \"https://www.googleapis.com/robot/v1/metadata/x509/k8s-gcr-auth-ro%40langame-dev.iam.gserviceaccount.com\"\n}","email":"louis.beaumont@gmail.com","auth":"X2pzb25fa2V5OnsKICAidHlwZSI6ICJzZXJ2aWNlX2FjY291bnQiLAogICJwcm9qZWN0X2lkIjogImxhbmdhbWUtZGV2IiwKICAicHJpdmF0ZV9rZXlfaWQiOiAiYzQ3N2M5NjBlOGMzYTFiM2E4Y2E3NjJmMDk3YTE5OTA1OTRkMDU4YyIsCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZBSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS1l3Z2dTaUFnRUFBb0lCQVFDOU9WOGUrbUxXNG9KbVxucWZPdGhteTArRXZOSW1LVEpGdzg3Q0wvOUxjbW1ZTjgra0YvbXBqUGpGY3daR1k4T1hLNTFVZWxYUjkxVnowVlxuNVVuTzlMbTkwTURYalpKZ0xUbjdZaytyc0ROUVJNNWUxOWM0VVVlMVNTWElVNGUxUGxNdTB6NEhKVmMxanh2Y1xua21XNXhHTjEzNlpHWDA4SE5Gc2FLUTNRc0x4WjNyRmJza0FUd0NNaUMxL1NJRmRBTmZHeGYyTWJnd0t1MEh3MFxueU81N3dFSWlCa1FlQkR6ZzBTOGowS0l6ZGdTNnVJMGpydDM4WXlzd2V5dk5qU21YL2tUTGJhVzE2ZTlieWdpTFxuL29rZHNFSUdCdFpFK2IzYXZBWkV2Z1g0WTJYbU5QYnVKb21iY3I0anRxcG9ITG9FOTJSSXVqc0o4TXRhUnZDQVxuY2JlYyt1MVBBZ01CQUFFQ2dnRUFRS09lRWxOL094K3lZd2F3ZHJrQ1hvbXBQMEI5UXYxN1F0WjVtRTBNMmJNOFxuUHcrd0d6cUE4L2xoZVdiNm81ME9TMXdIdHY0S05vZmdGcUEyWit1aW5heDNpOHJSVTJodnM2ZWdScXFReE4xVVxuVUFMVWd1a0ZJWEVFNXB0ZU12UkE3ekI3TW02M2pWUy9ORWlRVm5hM2NUYytzakJ4cXlqZjdCNVZHVktlYk9ZMlxuRzFnREkya3JFZzhxSU8vZURxczZwb0JMR3NJTXVqZUVKQW91MlE1M2Y1aWgwZlZBQ1JFN20yUk1kNklCemFVbVxuODIxS3kvZVlpbkdKeDhFY0lPd0dtZGMzU1YrRUpKN09SbWo5S2dreGtGV0xtZ2tQVWRGNjdmRVpmR1p2aldEK1xua3dnSEhNUERpT3BoTDJTb054Z1AxVHNaT0xFRURLVEVGd0puWkV2V3lRS0JnUUQxRXY0TFZCeWxFcTQ1RDdIVlxuQnd5UW9wNk5PWURsQ09GY0NDV0dHZTZIendmM2dZSTN5Z3d4MTFIZlppVzB5U2QrWGFTbU83bkZ0aE0xalRONVxua2tpYnBza1JYN2RGS3hRQUtINDlFSGxnTUQ0MjB4NW05emNGVEJvNW9GY2xIR3lJT2VmWG5UdjYzMUhlSjkxbVxuZkNDUjZwMHhqY1M0eVVxRWhIdGdrY0pRYVFLQmdRREZxUGU4UU8rVXIrdGF0Uk5ndmNmcnpTM3NTZjczTk4rNVxuZEJ2WkFKRXRTT2FJWFJtcm1HcDVYZHJBUTZTVk9IVkg5dkJQTVBjeHFucE5EK3M2TDB2NUVFU1U0UHgyZzZCaFxud3dVZjZCMkVyNGJjZEh3b0VkbTlXM1hhZU1sNnJnWW9xaW53YjVxMDM4MHJVdUhteVFhdGlFVG4wcXpEc3BubVxudkR3L3JKbVk5d0tCZ0RWUVVXWERnWXZEbVpVZVBmQjYzUmZsMkpvZVpWVHQ3cUNud1FvQVFDelpOQUY2OGdvU1xuOFQ0eWVrUWdJNW5Gbk1yWHNrYmJmVmx1ZDVWUngxM3VIYytHby8wY2xuRDhveGc1dHVTdjNjZTRGd0MwUXN2aFxuZ2Qyc0paUmR0amVEakhUQ0xCWnl4U2FaU0dVTXhSUlRjbjVyekpDSUo4Q1BRWis4ZGw2V3R1L3BBb0dBWkVSalxuYjFiTmNmS1BoRk1Jd25GaklnWFNQdVFHZDZhVnV3RGdRNE5iSWNxeVR3aFRSazJwN1drajE1WTR2ZzJHeVB2R1xuU1pYQVA2eUlIK0ZzWlBhckptd1BMaXEzUnZOY2Yxc3JsVlRzN0dzU0VYRHhybTNuczN2YTIvbWIweVRHTVFpb1xuLzdQTm1lVlJzYUY0d05iSEVXNW43ZVZjQ0dYb1ZqaTBvMlJPQWw4Q2dZQjFOYk5TUCs4a0xmL1g5YVhqL3ZFQ1xuU2pqYnRJN294dUhzeW1lMzlvQ1h1RExwcm5GUHRGTTNZVzN0Y0lVcDI1QWY4NnYxa2oybUltK2NUVlkyQWFqL1xudTlNNlV5SnRWNXRYZkRFT3lKNC90R0gwdHk3QXJrYnhQTGRpS0F2U1VNbU9aTGxyYVhkRFVlYUwycTdINkFhaFxuL1M4K3lCazJ5WTJFVWJuSzFwNjB6dz09XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLAogICJjbGllbnRfZW1haWwiOiAiazhzLWdjci1hdXRoLXJvQGxhbmdhbWUtZGV2LmlhbS5nc2VydmljZWFjY291bnQuY29tIiwKICAiY2xpZW50X2lkIjogIjExMzQ4MzcxMTM2MTI3MTYyMDk3NCIsCiAgImF1dGhfdXJpIjogImh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbS9vL29hdXRoMi9hdXRoIiwKICAidG9rZW5fdXJpIjogImh0dHBzOi8vb2F1dGgyLmdvb2dsZWFwaXMuY29tL3Rva2VuIiwKICAiYXV0aF9wcm92aWRlcl94NTA5X2NlcnRfdXJsIjogImh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL29hdXRoMi92MS9jZXJ0cyIsCiAgImNsaWVudF94NTA5X2NlcnRfdXJsIjogImh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL3JvYm90L3YxL21ldGFkYXRhL3g1MDkvazhzLWdjci1hdXRoLXJvJTQwbGFuZ2FtZS1kZXYuaWFtLmdzZXJ2aWNlYWNjb3VudC5jb20iCn0="}}}