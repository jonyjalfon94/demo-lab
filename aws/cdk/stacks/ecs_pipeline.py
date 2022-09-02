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
    aws_ecr as ecr,
)

class ECSPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, ecs_service, app_root_dir, service_name, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.prefix = service_name

        # Create a ECR repo
        self.ecr_repo = ecr.Repository(
            self, f"{self.prefix}-ecr-repo",
            repository_name=f"{self.prefix}"
        )

        # Create a CodeCommit repository
        self.code_commit_repo = codecommit.Repository(
            self, f"{self.prefix}-repo",
            repository_name= f"{self.prefix}"
        )
        
        # Codebuild project
        build_project = codebuild.PipelineProject(
            self, f"{self.prefix}Project",
            project_name= f"{self.prefix}-build-push-ecs",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "build": {
                        "commands": [   
                            "$(aws ecr get-login --region $AWS_DEFAULT_REGION --no-include-email)",
                            f"cd {app_root_dir}",
                            "docker build -t $REPOSITORY_URI:latest .",
                            "docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "cd -"
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "docker push $REPOSITORY_URI:latest",
                            "docker push $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "export imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION",
                            "printf '[{\"name\":\"app\",\"imageUri\":\"%s\"}]' $REPOSITORY_URI:$imageTag > imagedefinitions.json"
                        ]
                    }
                },
                "env": {
                    # save the imageTag environment variable as a CodePipeline Variable
                     "exported-variables": ["imageTag"]
                },
                "artifacts": {
                    "files": "imagedefinitions.json",
                    "secondary-artifacts": {
                        "imagedefinitions": {
                            "files": "imagedefinitions.json",
                            "name": "imagedefinitions"
                        }
                    }
                }
            }),
            environment_variables={
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=self.ecr_repo.repository_uri)
            },
            environment=codebuild.BuildEnvironment(
                privileged=True
            )
        )

        # Grant push pull permissions on ecr repo to code build project needed for `docker push`
        self.ecr_repo.grant_pull_push(build_project.role)
        
        # Create a source output
        source_output = codepipeline.Artifact()

        # Source action
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name='CodeCommit',
            repository=self.code_commit_repo,
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
            outputs=[codepipeline.Artifact('imagedefinitions')]
        )

        # Build stage
        build_stage = codepipeline.StageProps(
            stage_name='Build',
            actions=[build_action]
        )

        # Deploy to ecs action
        deploy_action = codepipeline_actions.EcsDeployAction(
            action_name='DeployToEcs',
            service=ecs_service,
            input=codepipeline.Artifact('imagedefinitions')
        )

        # Deploy stage
        deploy_stage = codepipeline.StageProps(
            stage_name='Deploy',
            actions=[deploy_action]
        )

        # Create pipeline
        codepipeline.Pipeline(
            self, f"{self.prefix}Pipeline",
            pipeline_name=f"{self.prefix}-pipeline-ecs",
            stages=[source_stage, build_stage, deploy_stage],
        )
        
        # Output the repo clone url
        CfnOutput(
            self, 'RepoCloneUrl',
            value=self.code_commit_repo.repository_clone_url_http
        )