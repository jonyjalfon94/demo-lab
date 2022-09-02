#!/usr/bin/env python3

import aws_cdk as cdk

from stacks.infrastructure import InfrastructureStack
from stacks.ecs_service import ECSFargateService
from stacks.ecs_pipeline import ECSPipelineStack
from stacks.eks_pipeline import EKSPipelineStack

app = cdk.App()

infra = InfrastructureStack(app, "Infrastructure")

# -------- Base --------
service_name = "hello-world"

ecs_service = ECSFargateService(app, "Helloworld",
    service_name=service_name,
    ecs_cluster=infra.ecs_cluster
)

ecs_pipeline = ECSPipelineStack(app, "PipelineECS",
    app_root_dir=service_name,
    ecs_service=ecs_service.fargate_service.service,
    service_name=service_name,
)

# -------- Bonus --------

# For the bonus, i'll be using the same ecr and code commit repository that were created in the ECSPipelineStack
eks_pipeline = EKSPipelineStack(app, "PipelineEKS",
    app_root_dir=service_name,
    service_name=service_name,
    ecr_repo=ecs_pipeline.ecr_repo,
    code_commit_repo=ecs_pipeline.code_commit_repo,
    eks_cluster_name=infra.eks_cluster.cluster_name,
    namespace="default"
)

app.synth()