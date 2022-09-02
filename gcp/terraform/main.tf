locals {
  cluster_type           = "demo-autopilot"
  network_name           = "demo-autopilot-public-network"
  subnet_name            = "demo-autopilot-public-subnet"
  master_auth_subnetwork = "demo-autopilot-public-master-subnet"
  pods_range_name        = "ip-range-pods-demo-autopilot-public"
  svc_range_name         = "ip-range-svc-demo--autopilot-public"
  subnet_names           = [for subnet_self_link in module.gcp-network.subnets_self_links : split("/", subnet_self_link)[length(split("/", subnet_self_link)) - 1]]
}

data "google_client_config" "default" {}

module "gke" {
  source                          = "terraform-google-modules/kubernetes-engine/google//modules/beta-autopilot-public-cluster"
  project_id                      = var.project_id
  name                            = "${local.cluster_type}-cluster"
  regional                        = true
  region                          = var.region
  network                         = module.gcp-network.network_name
  subnetwork                      = local.subnet_names[index(module.gcp-network.subnets_names, local.subnet_name)]
  ip_range_pods                   = local.pods_range_name
  ip_range_services               = local.svc_range_name
  release_channel                 = "REGULAR"
  enable_vertical_pod_autoscaling = true
  create_service_account          = false
}

resource "helm_release" "ingress-nginx" {
  name = "ingress-nginx"
  chart = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  namespace = "ingress-nginx"
  create_namespace = true
  depends_on = [
    module.gke,
  ]
}