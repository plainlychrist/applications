The `file:///...` should contain the path to the Cloud Formation JSON (in this directory).

```bash
aws --profile site-dev cloudformation create-stack --parameters ParameterKey=AsgMaxSize,ParameterValue=1 ParameterKey=CreateElasticLoadBalancer,ParameterValue=false ParameterKey=DrupalDBAllocatedStorage,ParameterValue=5 ParameterKey=DrupalDBEngine,ParameterValue=MySQL ParameterKey=DrupalDBInstanceClass,ParameterValue=db.t2.micro ParameterKey=DrupalDBName,ParameterValue=drupal ParameterKey=DrupalDBPassword,ParameterValue=YOUR_DRUPAL_DATABASE_PASSWORD ParameterKey=WebAdminPassword,ParameterValue=YOUR_WEB_ADMIN_PASSWORD ParameterKey=DrupalDBUser,ParameterValue=drupal ParameterKey=DrupalMultiAZDatabase,ParameterValue=false ParameterKey=EcsAmiId,ParameterValue=ami-2d1bce4d ParameterKey=EcsClusterName,ParameterValue=default ParameterKey=EcsInstanceType,ParameterValue=t2.micro ParameterKey=EcsPort,ParameterValue=80 ParameterKey=ElbHealthCheckTarget,ParameterValue=HTTP:80/ ParameterKey=ElbPort,ParameterValue=80 ParameterKey=ElbProtocol,ParameterValue=HTTP ParameterKey=IamRoleInstanceProfile,ParameterValue=ecsInstanceRole ParameterKey=KeyName,ParameterValue=ecs-login ParameterKey=SourceCidr,ParameterValue=50.46.233.3/32 --stack-name plainlychrist-%RANDOM% --template-url file:///...
```

For example:

```bash
sudo yum install expect
MYPWD=$(mkpasswd -s 0 -l 40)
DRPWD=$(mkpasswd -s 0 -l 40)
aws --profile site-dev cloudformation create-stack --parameters ParameterKey=AsgMaxSize,ParameterValue=1 ParameterKey=CreateElasticLoadBalancer,ParameterValue=false ParameterKey=DrupalDBAllocatedStorage,ParameterValue=5 ParameterKey=DrupalDBEngine,ParameterValue=MySQL ParameterKey=DrupalDBInstanceClass,ParameterValue=db.t2.micro ParameterKey=DrupalDBName,ParameterValue=drupal ParameterKey=DrupalDBPassword,ParameterValue="${DRPWD}" ParameterKey=WebAdminPassword,ParameterValue="${MYPWD}" ParameterKey=DrupalDBUser,ParameterValue=drupal ParameterKey=DrupalMultiAZDatabase,ParameterValue=false ParameterKey=EcsAmiId,ParameterValue=ami-2d1bce4d ParameterKey=EcsClusterName,ParameterValue=default ParameterKey=EcsInstanceType,ParameterValue=t2.micro ParameterKey=EcsPort,ParameterValue=80 ParameterKey=ElbHealthCheckTarget,ParameterValue=HTTP:80/ ParameterKey=ElbPort,ParameterValue=80 ParameterKey=ElbProtocol,ParameterValue=HTTP ParameterKey=IamRoleInstanceProfile,ParameterValue=ecsInstanceRole ParameterKey=KeyName,ParameterValue=ecs-login ParameterKey=SourceCidr,ParameterValue=50.46.233.3/32 --stack-name plainlychrist-$RANDOM --template-url file:///...
echo "Drupal Password: $DRPWD"
```
