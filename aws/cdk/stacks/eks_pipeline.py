from email.mime import image
from tkinter import Y
from constructs import Construct
from aws_cdk import (
    Stack,
    CfnOutput,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_ssm as ssm,
    aws_ecr as ecr,
    aws_iam as iam,
)

class EKSPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, app_root_dir, service_name, code_commit_repo, ecr_repo, namespace, eks_cluster_name, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.prefix = service_name

        # import parameter from parameter store
        self.param = ssm.StringParameter.from_string_parameter_attributes(
            self, "Parameter",
            parameter_name="/demo/deployer-role-arn"
        )

        # Import role from arn
        self.role = iam.Role.from_role_arn(
            self, "Role",
            role_arn=self.param.string_value
        )

        # Codebuild project
        build_project = codebuild.PipelineProject(
            self, f"{self.prefix}EKSProject",
            project_name= f"{self.prefix}-build-push-eks",
            role=self.role,
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install" : {
                        "commands": [
                            "curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash"
                        ]
                    },
                    "build": {
                        "commands": [   
                            "$(aws ecr get-login --region $AWS_DEFAULT_REGION --no-include-email)",
                            f"cd {app_root_dir}",
                            "docker build -t $REPOSITORY_URI:latest .",
                            "docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "cd -",
                            "docker push $REPOSITORY_URI:latest",
                            "docker push $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "export imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION",
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo \"Update Kube Config\"",
                            "aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $AWS_DEFAULT_REGION",
                            "echo \"Deploying to EKS\"",
                            f"cd {app_root_dir}",
                            "helm upgrade --install --wait --timeout 600 --namespace $EKS_NAMESPACE --set image.repository=$REPOSITORY_URI --set image.tag=$imageTag $SERVICE_NAME {app_root_dir}/helm",
                        ]
                    }
                },
                "env": {
                    # save the imageTag environment variable as a CodePipeline Variable
                     "exported-variables": ["imageTag"]
                }
            }),
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=Stack.of(self).region),
                "EKS_CLUSTER_NAME": codebuild.BuildEnvironmentVariable(value=eks_cluster_name),
                "EKS_NAMESPACE": codebuild.BuildEnvironmentVariable(value=namespace),
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=ecr_repo.repository_uri),
                "SERVICE_NAME": codebuild.BuildEnvironmentVariable(value=service_name),
            },
            environment=codebuild.BuildEnvironment(
                privileged=True
            )
        )

        # Grant push pull permissions on ecr repo to code build project needed for `docker push`
        ecr_repo.grant_pull_push(build_project.role)
        
        # Create a source output
        source_output = codepipeline.Artifact()

        # Source action
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name='CodeCommit',
            repository=code_commit_repo,
            output=source_output,
            trigger=codepipeline_actions.CodeCommitTrigger.POLL,
            code_build_clone_output=True
        )

        # Source stage
        source_stage = codepipeline.StageProps(
            stage_name='Source',
            actions=[source_action]
        )

        # Build action
        build_action = codepipeline_actions.CodeBuildAction(
            action_name='CodeBuild',
            project=build_project,
            input=source_output,
        )

        # Build stage
        build_stage = codepipeline.StageProps(
            stage_name='Build',
            actions=[build_action]
        )

        # Create pipeline
        codepipeline.Pipeline(
            self, f"{self.prefix}EKSPipeline",
            pipeline_name=f"{self.prefix}-pipeline-eks",
            stages=[source_stage, build_stage],
        )
        
        # Output the repo clone url
        CfnOutput(
            self, 'RepoCloneUrl',
            value=code_commit_repo.repository_clone_url_http
        )