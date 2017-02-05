# Parameters

## ECS_AMI_ID

You can use the default, or pick the latest [AWS ECS Optimized AMI](http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html) for `us-west-2`.

## MY_IP

You can find your IP address at [Google's "Your Public IP Address"](https://www.google.com/search?q=what+is+my+ip)

## SSH_KEY_NAME

You can use an existing EC2 key pair, import a key pair, or generate a new one at [EC2 Key Pairs Management for us-west-2](https://us-west-2.console.aws.amazon.com/ec2/v2/home?region=us-west-2#KeyPairs:sort=keyName). You can find more information at [Amazon EC2 Key Pairs](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html)

You'll need this key pair to log into the newly launched EC2 instances.

# Launching

For example, in this directory run the following after setting `MY_IP` and `ECS_AMI_ID` and `SSH_KEY_NAME` correctly:

```bash
MY_IP=50.46.233.3
ECS_AMI_ID=ami-56ed4936
SSH_KEY_NAME=ecs-login

sudo yum install expect

MYPWD=$(mkpasswd -s 0 -l 40)
DRPWD=$(mkpasswd -s 0 -l 40)
aws --profile site-dev cloudformation create-stack --parameters ParameterKey=DrupalDBAllocatedStorage,ParameterValue=5 ParameterKey=DrupalDBEngine,ParameterValue=MySQL ParameterKey=DrupalDBInstanceClass,ParameterValue=db.t2.micro ParameterKey=DrupalDBName,ParameterValue=drupal ParameterKey=DrupalDBPassword,ParameterValue="${MYPWD}" ParameterKey=WebAdminPassword,ParameterValue="${DRPWD}" ParameterKey=DrupalDBUser,ParameterValue=drupal ParameterKey=DrupalMultiAZDatabase,ParameterValue=false ParameterKey=EcsAmiId,ParameterValue=${ECS_AMI_ID} ParameterKey=EcsInstanceType,ParameterValue=t2.micro ParameterKey=IamRoleInstanceProfile,ParameterValue=ecsInstanceRole ParameterKey=KeyName,ParameterValue=${SSH_KEY_NAME} ParameterKey=SourceCidr,ParameterValue=${MY_IP}/32 --stack-name pc-$RANDOM --template-body "$(cat cloudformation.yaml)"
echo "Drupal Password: $DRPWD"
```

## Using a SSL certificate

You'll need to register or create an SSL certificate in the AWS Certificate Manager.

Add to the `--parameters` an ARN from the AWS Certificate Manager and the website protected by the certificate. Here is an example:

```bash
ParameterKey=ElbSSLCertificateArn,ParameterValue=arn:aws:acm:us-west-2:123456789012:certificate/333af33a-3333-3cb3-333a-3a33b33a3333 ParameterKey=ElbSSLCertificateCommonName,ParameterValue=xyz.yoursite.org
```

## Using more than one machine

Add to the `--parameters` the number of machines:
```bash
ParameterKey=AsgMaxSize,ParameterValue=2 ParameterKey=CreateElasticLoadBalancer,ParameterValue=true ParameterKey=DrupalHashSalt,ParameterValue=$(openssl rand -base64 64 | tr -d '\n')
```

## Custom Cloudwatch Metrics for Elastic FileSystem

If you were to log into one of the ECS instances and run:

```bash
 /usr/sbin/nfsstat | /home/ec2-user/post_nfsstat
```

you may see:

```
An error occurred (AccessDenied) when calling the PutMetricData operation: User: arn:aws:sts::138948531757:assumed-role/ecsInstanceRole/i-0d5b7dc467e609d24 is not authorized to perform: cloudwatch:PutMetricData
```

If you do see this error, you need to go to [AWS Console > IAM > Roles > ecsInstanceRole for us-west-2](https://console.aws.amazon.com/iam/home?region=us-west-2#roles/ecsInstanceRole) and expand the `Inline Policies`.

Create a role policy, using a `Custom Policy` with the `Policy Name` = `CloudwatchPut` and `Policy Document` =:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```
