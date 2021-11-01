FROM gitpod/workspace-full-vnc:latest
USER root
# gcloud CLI
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" |\
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list &&\
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg |\
    apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - &&\
    apt-get update -y &&\
    apt-get install google-cloud-sdk -y &&\
    curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 &&\
    chmod 700 get_helm.sh &&\
    ./get_helm.sh &&\
    rm -rf ./get_helm.sh &&\
    curl -sfL https://get.k3s.io | sh -

ENV KUBECONFIG $HOME/.kube/config

USER gitpod