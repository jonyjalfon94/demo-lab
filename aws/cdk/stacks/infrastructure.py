from importlib.util import resolve_name
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_eks as eks,
    aws_iam as iam,
    aws_ssm as ssm,
    CfnOutput, Stack
)
from constructs import Construct

class InfrastructureStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(
            self, "demo-vpc",
            max_azs=2
        )

        # Create a cluster
        self.ecs_cluster = ecs.Cluster(
            self, "demo-cluster",
            cluster_name="demo-ecs-cluster",
            vpc=vpc
        )
        
        # ------------ BONUS ------------

        # Define IAM Policy for EKS
        eks_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "eks:DescribeCluster",
                    ],
                    resources=["*"]
                ),
            ]
        )

        # Define cluster admin role
        self.cluster_admin_role = iam.Role(
            self, "demo-cluster-admin-role",
            role_name="demo-cluster-admin-role",
            inline_policies={
                "demo-eks-policy": eks_policy
            },
            assumed_by=iam.AccountRootPrincipal()
        )

        # Define deployer role
        self.deployer_role = iam.Role(
            self, "demo-deployer-role",
            role_name="demo-deployer-role",
            inline_policies={
                "demo-eks-policy": eks_policy
            },
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
        )

        # Save deployer role ARN in parameter store
        self.deployer_role_arn_param = ssm.StringParameter(
            self, "demo-deployer-role-arn-param",
            parameter_name="/demo/deployer-role-arn",
            string_value=self.deployer_role.role_arn
        )

        # Create EKS cluster
        self.eks_cluster = eks.Cluster(
            self, f"demo-eks-cluster",
            cluster_name="demo-eks-cluster",
            version=eks.KubernetesVersion.V1_21,
            default_capacity=1,
            default_capacity_instance=ec2.InstanceType("t3.medium"),
            vpc=vpc,
            masters_role=self.cluster_admin_role
        )

        # Add deployer role to aws-auth configmap
        self.eks_cluster.aws_auth.add_role_mapping(
            self.deployer_role,
            groups=["system:masters"]
        )

        # Add ingress controller to the cluster
        self.eks_cluster.add_helm_chart("ingress-nginx",
            chart="ingress-nginx",
            repository="https://kubernetes.github.io/ingress-nginx",
            release=f"demo-ingress-nginx",
            namespace="ingress-nginx",
        )

        # Add cluster admin role arn as output
        CfnOutput(
            self, "demo-cluster-admin-role-arn",
            value=self.cluster_admin_role.role_arn
        )
