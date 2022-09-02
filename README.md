# Prerequisites

In this demo we are using a self signed certificate in order to serve traffic through Https.
To attach a certificate to the ALB that will be serving requests, a certificate must be imported to ACM before deploying the `HelloCommit` Stack.

## Procedure


1. Generate the certificate (The CN of the certificate is `*.amazonaws.com` to use AWS provided DNS)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout selfsigned.key -out selfsigned.crt -subj "/CN=*.amazonaws.com"
```

2. Import the certificate to ACM

```bash
aws acm import-certificate --certificate fileb://selfsigned.crt --private-key fileb://selfsigned.key --tags Key=Name,Value=self-signed-demo
```

# Deployment

We will be using CDK to synthetize CloudFormation templates that deploy the demo hello-world service into `ecs` and `eks` by using CodePipeline with CodeDeploy and CodeCommit.

## Procedure

1. To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

2. After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

3. If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

4. Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

5. At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth --all
```

7. In case it is the first time deploying with CDK into this account use CDK bootstrap
```
cdk bootstrap
```

6. Add your certificate ARN to cdk.json context
```
  },
  "context": {
    "@aws-cdk/aws-apigateway:usagePlanKeyOrderInsensitiveId": true,
    "@aws-cdk/core:stackRelativeExports": true,
    "@aws-cdk/aws-rds:lowercaseDbIdentifier": true,
    "@aws-cdk/aws-lambda:recognizeVersionProps": true,
    "@aws-cdk/aws-cloudfront:defaultSecurityPolicyTLSv1.2_2021": true,
    "acm_certificate_arn": "arn:aws:acm:eu-west-1:434834777527:certificate/b7346d87-1ae1-4b61-9836-80e646c434d1" # <-- This Line
  }
}
```

7. Deploy with CDK
```
cdk deploy --all
```

8. Once cdk is done provisioning the infrastructure, take the git repo url from the outputs and push the repo to Code Commit. This will trigger both EKS and ECS pipelines.

9. Once the pipeline is done running is time to check the changes were deployed:
  
- ECS
  - Browse to the alb dns from the cdk output
- EKS
  - Assume the cluster-admin-role (ARN from cdk output)
  - Get the kubeconfig of the cluster `aws eks update-kubeconfig --name <cluster-name>`
  - Get the ingress lb dns `kubectl get svc -n ingress-nginx`
  - Browse to the ingress lb dns

## Other Useful CDK commands

 * `cdk ls`          list all stacks in the app
 * `cdk bootstrap`   deploys the CDK toolkit stack into an AWS environment
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

# Extra GCP Bonus

As i didn't use Terraform for the lab, i added a small bonus that uses Terraform to provision a GKE autopilot cluster and Github Actions for the CI/CD pipeline.

NOTE: I do not own a GCP account so i'm using acloudguru ephemeral sandboxes so there is no need for storing the state terraform state as i'm running the code locally.

## Prerequisites

1. Before deploying to GCP ensure you have the required APIs enabled
```bash
gcloud services enable container.googleapis.com && \
gcloud services enable containerregistry.googleapis.com 
```

2. Ensure you have a valid credentials file to deploy with terraform
```
gcloud auth application-default login
```

## Procedure

1. CD into the terraform directory
```bash
cd ./gcp/terraform
```

2. Initialize providers and modules
```
terraform init
```

3. Check Infrastructure that will be provisioned
```
terraform plan
```

4. Provision infrastructure
```
terraform apply
```