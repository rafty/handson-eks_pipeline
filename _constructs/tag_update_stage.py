import os
import subprocess
import aws_cdk
from constructs import Construct
from aws_cdk import aws_codepipeline_actions
from aws_cdk import aws_lambda
from aws_cdk import aws_iam


class TagUpdateStage(Construct):
    # ----------------------------------------------------------
    # Stage - Manifest Tag Update (GitHub)
    # ----------------------------------------------------------

    def __init__(self, scope: Construct, id: str, info: dict, env: dict, **kwargs) -> None:
        super().__init__(scope, id)
        self._region = env.get('region')
        # self._container_image_name = info.get('container_image_name')  # from Build Stage
        self._container_image_tag = info.get('container_image_tag')  # from Build Stage
        self._git_layer = self.create_lambda_layer()
        # self.source_output = aws_codepipeline.Artifact('source_stage_output')

    def github_tag_update_action(self):
        # ----------------------------------------------------------
        # Stage - Manifest Tag Update (GitHub)
        # ----------------------------------------------------------
        github_target_repository = self.node.try_get_context('github_target_repository')
        github_target_manifest = self.node.try_get_context('github_target_manifest')
        github_token_name = self.node.try_get_context('github_token_name')

        fn = self.create_lambda_function()
        lambda_invoke_action = aws_codepipeline_actions.LambdaInvokeAction(
            action_name='github-manifest-tag-update',
            user_parameters={
                'github_target_repository': github_target_repository,
                'github_target_manifest': github_target_manifest,
                'github_branch': 'master',
                'github_token_name': github_token_name,
                # 'container_image_name': self._container_image_name,  # from Build Stage
                'container_image_tag': self._container_image_tag,  # from Build Stage
            },
            lambda_=fn,
        )
        return lambda_invoke_action

    def create_lambda_role(self):
        lambda_role = aws_iam.Role(
            self,
            id='LambdaRole',
            assumed_by=aws_iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                # Adding Policies
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaBasicExecutionRole'),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchFullAccess'),
                # aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
                # aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSCodePipeline_FullAccess'),
                # aws_iam.ManagedPolicy.from_aws_managed_policy_name('AWSCodeDeployFullAccess'),
                # aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMFullAccess')
            ]
        )
        lambda_role.add_to_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=['secretsmanager:GetSecretValue'],
                resources=["*"]))
        lambda_role.add_to_policy(aws_iam.PolicyStatement(
            resources=["*"],
            actions=["sts:AssumeRole"]))
        return lambda_role

    def create_lambda_function(self):

        _powertools_layer = aws_lambda.LayerVersion.from_layer_version_arn(
            self,
            id='lambda-powertools',
            layer_version_arn=(f'arn:aws:lambda:{self._region}:017000801446:'
                               'layer:AWSLambdaPowertoolsPython:19')
        )

        lambda_role = self.create_lambda_role()

        # aws_iam.Policy(
        #     self,
        #     'LambdaPolicy',
        #     statements=[policy_statement],
        #     roles=[lambda_role]
        # )

        function = aws_lambda.Function(
            self,
            'LambdaInvokeFunction',
            function_name='GithubManifestTagUpdate',
            handler='function.lambda_handler',
            runtime=aws_lambda.Runtime.PYTHON_3_8,
            code=aws_lambda.Code.from_asset('./functions/manifest_update'),
            role=lambda_role,
            layers=[_powertools_layer, self._git_layer],
            environment={
                'POWERTOOLS_SERVICE_NAME': 'GitOpsPipelineAction',  # for Powertools
                'LOG_LEVEL': 'INFO',  # for Powertools
            },
            memory_size=128,
            timeout=aws_cdk.Duration.seconds(60),
            # dead_letter_queue_enabled=True
        )
        return function

    # def create_lambda_layer(self, project_name, function_name) -> aws_lambda.LayerVersion:
    def create_lambda_layer(self) -> aws_lambda.LayerVersion:
        # requirements_file = function_name + "/" + "requirements.txt"
        requirements_file = 'layers/git_command/requirements.txt'
        # output_dir = ".lambda_dependencies/" + function_name
        output_dir = "layer_pip/"

        # Install requirements for layer in the output_dir
        if not os.environ.get("SKIP_PIP"):
            # Note: Pip will create the output dir if it does not exist
            subprocess.check_call(
                f"pip install -r {requirements_file} -t {output_dir}/python".split()
            )
        return aws_lambda.LayerVersion(
            self,
            id='GitCommand',
            layer_version_name='GitCommand',
            code=aws_lambda.Code.from_asset(output_dir)
        )
