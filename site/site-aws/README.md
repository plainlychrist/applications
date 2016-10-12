# Parameters

## EcsAmiId

You can use the default, or pick the latest [AWS ECS Optimized AMI](http://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-optimized_AMI.html) for `us-west-2`.

## MY_IP

You can find your IP address at [Google's "Your Public IP Address"](https://www.google.com/search?q=what+is+my+ip)

# Launching

For example, in this directory run the following after setting `MY_IP` and `ECS_AMI_ID` correctly:

```bash
MY_IP=50.46.233.3
ECS_AMI_ID=ami-562cf236

sudo yum install expect

MYPWD=$(mkpasswd -s 0 -l 40)
DRPWD=$(mkpasswd -s 0 -l 40)
aws --profile site-dev cloudformation create-stack --parameters ParameterKey=DrupalDBAllocatedStorage,ParameterValue=5 ParameterKey=DrupalDBEngine,ParameterValue=MySQL ParameterKey=DrupalDBInstanceClass,ParameterValue=db.t2.micro ParameterKey=DrupalDBName,ParameterValue=drupal ParameterKey=DrupalDBPassword,ParameterValue="${MYPWD}" ParameterKey=WebAdminPassword,ParameterValue="${DRPWD}" ParameterKey=DrupalDBUser,ParameterValue=drupal ParameterKey=DrupalMultiAZDatabase,ParameterValue=false ParameterKey=EcsAmiId,ParameterValue=${ECS_AMI_ID} ParameterKey=EcsInstanceType,ParameterValue=t2.micro ParameterKey=IamRoleInstanceProfile,ParameterValue=ecsInstanceRole ParameterKey=KeyName,ParameterValue=ecs-login ParameterKey=SourceCidr,ParameterValue=${MY_IP}/32 --stack-name plainlychrist-$RANDOM --template-body "$(cat cloudformation.yaml)"
echo "Drupal Password: $DRPWD"
```

## Using a SSL certificate

You'll need to register or create an SSL certificate in the AWS Certificate Manager.

Add to the `--parameters` an ARN from the AWS Certificate Manager and the website protected by the certificate. Here is an example:

```bash
ParameterKey=ElbSSLCertificateId,ParameterValue=arn:aws:acm:us-west-2:123456789012:certificate/333af33a-3333-3cb3-333a-3a33b33a3333 ParameterKey=ElbSSLCertificateCommonName,ParameterValue=xyz.yoursite.org
```

## Using more than one machine

Add to the `--parameters` the number of machines:
```bash
ParameterKey=AsgMaxSize,ParameterValue=2 ParameterKey=CreateElasticLoadBalancer,ParameterValue=true ParameterKey=DrupalHashSalt,ParameterValue=$(openssl rand -base64 64 | tr -d '\n')
```
