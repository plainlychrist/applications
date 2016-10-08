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
aws --profile site-dev cloudformation create-stack --parameters ParameterKey=AsgMaxSize,ParameterValue=1 ParameterKey=CreateElasticLoadBalancer,ParameterValue=false ParameterKey=DrupalDBAllocatedStorage,ParameterValue=5 ParameterKey=DrupalDBEngine,ParameterValue=MySQL ParameterKey=DrupalDBInstanceClass,ParameterValue=db.t2.micro ParameterKey=DrupalDBName,ParameterValue=drupal ParameterKey=DrupalDBPassword,ParameterValue="${MYPWD}" ParameterKey=WebAdminPassword,ParameterValue="${DRPWD}" ParameterKey=DrupalDBUser,ParameterValue=drupal ParameterKey=DrupalMultiAZDatabase,ParameterValue=false ParameterKey=EcsAmiId,ParameterValue=${ECS_AMI_ID} ParameterKey=EcsClusterName,ParameterValue=default ParameterKey=EcsInstanceType,ParameterValue=t2.micro ParameterKey=IamRoleInstanceProfile,ParameterValue=ecsInstanceRole ParameterKey=KeyName,ParameterValue=ecs-login ParameterKey=SourceCidr,ParameterValue=${MY_IP}/32 --stack-name plainlychrist-$RANDOM --template-body "$(cat cloudformation.json)"
echo "Drupal Password: $DRPWD"
```
