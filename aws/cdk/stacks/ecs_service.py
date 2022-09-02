from importlib.util import resolve_name
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs_patterns as ecs_patterns,
    aws_certificatemanager as acm,
    CfnOutput, Stack
)
from constructs import Construct

class ECSFargateService(Stack):

    def __init__(self, scope: Construct, construct_id: str, ecs_cluster: ecs.Cluster, service_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id,  **kwargs)

        self.prefix = service_name

        # Create task role
        task_role = iam.Role(self, f"{self.prefix}-task-role",
            role_name=f"{self.prefix}-task-role",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )

        # Create policy for task execution role
        execution_role_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources=["*"]
        )

        # Create app log driver
        log_driver = ecs.AwsLogDriver(
            stream_prefix=f"ecs/{self.prefix}",
        )
        # Create Task Definition
        fargate_task_definition = ecs.FargateTaskDefinition(self, f"{self.prefix}-app",
            memory_limit_mib=512,
            cpu=256,
            execution_role=task_role,
        )

        # Add policy to task role
        fargate_task_definition.add_to_execution_role_policy(execution_role_policy)

        # Add Container
        fargate_task_definition.add_container("app",
            image=ecs.ContainerImage.from_registry("nginx:1.23.1-alpine"),
            port_mappings=[ecs.PortMapping(container_port=80)],
            logging=log_driver,
            essential=True
        )

        # Import certificate from ACM
        certificate = acm.Certificate.from_certificate_arn(self, f"{self.prefix}-cert",
            # Get certificate arn from context
            certificate_arn=self.node.try_get_context("acm_certificate_arn")
        )

        # Create Fargate Service
        self.fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, f"{self.prefix}",
            desired_count=1,
            cluster=ecs_cluster,
            task_definition=fargate_task_definition,
            listener_port=443,
            certificate=certificate
        )