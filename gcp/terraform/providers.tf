provider "google" {
  project = "playground-s-11-682254af"
  region  = "us-central1"
  zone    = "us-central1-c"
}

provider "kubernetes" {
  host                   = "https://${module.gke.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(module.gke.ca_certificate)
}

provider "helm" {
  kubernetes {
    cluster_ca_certificate = base64decode(module.gke.ca_certificate)
    host = "https://${module.gke.endpoint}"
    token = data.google_client_config.default.access_token
  }
}