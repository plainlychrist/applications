#!/usr/bin/env python3
# vim: autoindent smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python:
import sys, traceback
import readline
from os.path import expanduser
import subprocess
from datetime import datetime
import re
import random
import base64
import os
import json

autogen_params = ['NetworkIdFromDatabaseId', 'NetworkId', 'DatabaseId', 'ModificationTimestamp']

FLAVORSHORT = 'bb' # buildbarbuda
FLAVORLONG = 'buildbarbuda'

# import a text menu library
try:
    from cursesmenu import CursesMenu
    from cursesmenu.items import FunctionItem, SubmenuItem, CommandItem, ExitItem
except ImportError as e:
    print ("FATAL: %s. Please follow the installation instructions at http://curses-menu.readthedocs.io/en/latest/installation.html" % (e))
    sys.exit(1)

# stop 'terminal messed up when the application dies without restoring the terminal to its previous state'
from curses import wrapper

# import a file configuration library
try:
    import yaml
except ImportError as e:
    print ("FATAL: %s. Please follow the installation instructions at http://pyyaml.org/wiki/PyYAML#DownloadandInstallation" % (e))
    sys.exit(1)

# handle !Ref and other YAML constructors
def ref_constructor(loader, node):
    value = loader.construct_scalar(node)
    return { 'Ref' : value }
def sub_constructor(loader, node):
    value = loader.construct_scalar(node)
    return { 'Fn::Sub' : value }
def join_constructor(loader, node):
    value = loader.construct_sequence(node)
    return { 'Fn::Join' : value }
def getatt_constructor(loader, node):
    value = loader.construct_scalar(node)
    return { 'Fn::GetAtt' : value }
yaml.add_constructor(u'!Ref', ref_constructor)
yaml.add_constructor(u'!Sub', sub_constructor)
yaml.add_constructor(u'!Join', join_constructor)
yaml.add_constructor(u'!GetAtt', getatt_constructor)

def rlinput(prompt, defaultval=''):
   readline.set_startup_hook(lambda: readline.insert_text(defaultval))
   try:
      return input(prompt)
   finally:
      readline.set_startup_hook()

def deconstruct_stack_name(stack):
    m = re.match('{0}-([a-z]+)-([0-9]+)(-([0-9]+))?'.format(FLAVORSHORT), stack)
    # skip non-buildbarbuda stacks
    if m is None: return (None, None, None)

    # capture network id and possibly database id
    this_stacktype = m.group(1)
    this_network = m.group(2)
    this_database = m.group(4) # could be None

    return (this_stacktype, this_network, this_database)

def list_stacks(stage, filters=None):
    args = '' if filters is None else '--stack-status-filter {0}'.format(filters)
    cmd = 'aws --profile site-{} --output json --no-paginate cloudformation list-stacks {}'.format(stage, args)
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    jsonstr = p.stdout.read()
    output = json.loads(jsonstr)
    return output["StackSummaries"]

def acquire_compute_bindings(stage, stack, family, cis):
    # find all the new tasks for the Family
    cmd ='aws --profile site-{0} --no-paginate --output json ecs list-tasks --cluster {1} --family {1}-{2}'.format(stage,stack,family)
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    jsonstr = p.stdout.read()
    output = json.loads(jsonstr)
    tasks = output['taskArns']

    binds = set()
    if tasks is None or len(tasks) == 0: return binds

    # find out the bindings for the tasks
    cmd ='aws --profile site-{0} --no-paginate --output json ecs describe-tasks --cluster {1} --tasks {2}'.format(stage,stack,' '.join(tasks))
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    jsonstr = p.stdout.read()
    output = json.loads(jsonstr)
    for t in output['tasks']:
        ci = t['containerInstanceArn']
        cis.add(ci)

        for c in t['containers']:
            for n in c['networkBindings']:
                binds.add( (ci, n['hostPort']) )
    return binds

def describe_instances(stage, network, database):
    # take all EC2 instances that share the Drupal database
    cmd ='aws --profile site-{} --no-paginate --output json ec2 describe-instances --filters="Name=tag:{}:database-id,Values={}-database-{}-{}"'.format(stage, FLAVORLONG, FLAVORSHORT, network, database)
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    jsonstr = p.stdout.read()
    return json.loads(jsonstr)

class ConfigMenu:
    """
    Configuration menu
    """

    def __init__(self, preferencesfile, stage, stacktype, cloudparams):
        self.stage = stage
        self.stacktype = stacktype
        self.prefs = yaml.safe_load(preferencesfile)
        if self.prefs is None:
            self.prefs = {'Parameters': dict(), 'Types': dict()}
        if 'Types' not in self.prefs:
            self.prefs['Types'] = dict()
        self.preferencesfile = preferencesfile
        self.templatekeys = []
        for key,val in cloudparams.items():
            self.templatekeys.append(key)
            # Provide defaults for DrupalHashSalt
            if key not in self.prefs['Parameters'] and key == 'DrupalHashSalt':
                self.prefs['Parameters'][key] = base64.b64encode(os.urandom(64)).decode('utf-8')
            # Skip over autogenerated parameters
            if key in autogen_params:
                # Clean up preference files containing autogen parameters, in case some are newly autogen
                self.prefs['Parameters'].pop(key, None)
                self.prefs['Types'].pop(key, None)
                continue
            # Provide defaults based on 'Default' in cloudformation-*.yaml
            if key not in self.prefs['Parameters'] and 'Default' in val:
                self.prefs['Parameters'][key] = val['Default']
            if 'Type' in val:
                self.prefs['Types'][key] = val['Type']
        self.parameters_menu = self.construct_parameters_menu(cloudparams)
        self.stacks_menu = self.construct_stacks_menu(cloudparams)

    def change_param(self, key):
        if key in self.prefs['Parameters']: s = rlinput('--> %s: ' % (key,), self.prefs['Parameters'][key])
        else: s = rlinput('--> %s: ' % (key,))
        self.prefs['Parameters'][key] = s

    def form_params(self, network, database):
        s = ''
        for key in self.prefs['Parameters']:
            # Not all of our preferences are usable by this CloudFormation template
            if key not in self.templatekeys: continue
            # We'll do the autogenerated parameters below
            if key in autogen_params: continue

            p = self.prefs['Parameters'][key]
            if 'CommaDelimitedList' == self.prefs['Types'][key]:
                p = p.replace(',', '\,')
            s += " ParameterKey=%s,ParameterValue='%s'" % (key, p)

        # Make ModificationTimestamp like 20170129T013016370623
        modts = datetime.utcnow().isoformat('T').translate(str.maketrans('', '', ':-.'))
        s += " ParameterKey=ModificationTimestamp,ParameterValue='%s'" % (modts,)

        # If we have DatabaseId=123-456, then produce NetworkIdFromDatabaseId=123
        if self.stacktype == 'database':
            s += " ParameterKey=NetworkId,ParameterValue='{0}'".format(network)
        if self.stacktype == 'compute':
            s += " ParameterKey=NetworkIdFromDatabaseId,ParameterValue='{0}'".format(network)
            s += " ParameterKey=DatabaseId,ParameterValue='{0}-{1}'".format(network, database)
        return s

    def common_stack_params(self, network, database):
        s = ' --parameters'
        s += self.form_params(network, database)
        s += ' --template-body "$(cat cloudformation-{0}.yaml)"'.format(self.stacktype)
        s += ' --tags Key={0}:stacktype,Value={1}'.format(FLAVORLONG, self.stacktype)
        return s

    def handle_menu_error(self):
        #e = sys.exc_info()
        traceback.print_exc(file = sys.stdout)
        #print(e)
        # since we are in Curses, we need to input() to see anything
        input('Press Enter to continue ... ')

    def create_stack(self, network, database):
        try:
            s = 'aws --profile site-{} --output text cloudformation create-stack'.format(self.stage)
            if self.stacktype == 'network':
                ident = '{0:05d}'.format(random.randrange(0,100000))
            elif self.stacktype == 'database':
                if network is None:
                    print('No network found')
                    input('Press Enter to continue ... ')
                    return
                ident = '{0}-{1:05d}'.format(network, random.randrange(0,100000))
            elif self.stacktype == 'compute':
                if network is None or database is None:
                    print('No database (or network) found')
                    input('Press Enter to continue ... ')
                    return
                ident = '{0}-{1}-{2:05d}'.format(network, database, random.randrange(0,100000))
            else:
                raise Exception('Unrecognized stacktype {0}'.format(self.stacktype))
            s += " --stack-name '{0}-{1}-{2}'".format(FLAVORSHORT, self.stacktype, ident)
            s += self.common_stack_params(network, database)
            print(s)
            subprocess.call (s, shell=True)
            input('Press Enter to continue ... ')
        except:
            self.handle_menu_error()
            raise


    def create_changeset_stack(self, stack, network, database):
        try:
            changets = datetime.utcnow().isoformat('T').translate(str.maketrans('', '', ':-.'))
            s = 'aws --profile site-{} --output text cloudformation create-change-set'.format(self.stage)
            s += " --stack-name '{0}'".format(stack)
            s += " --change-set-name '{0}-{1}'".format(stack, changets)
            s += self.common_stack_params(network, database)
            print(s)
            subprocess.call (s, shell=True)
            input('Press Enter to continue ... ')
        except:
            self.handle_menu_error()
            raise

    def update_stack(self, stack, network, database):
        try:
            s = 'aws --profile site-{} --output text cloudformation update-stack'.format(self.stage)
            s += " --stack-name '{0}'".format(stack)
            s += self.common_stack_params(network, database)
            print(s)
            subprocess.call (s, shell=True)
            input('Press Enter to continue ... ')
        except:
            self.handle_menu_error()
            raise

    def mark_compute_stack(self, stack, network, database):
        try:
            # find all EC2 instances that share the Drupal database
            output = describe_instances(self.stage, network, database)

            thehostnames = []
            for r in output["Reservations"]:
                for i in r["Instances"]:
                    pbdns = i["PublicDnsName"]
                    if len(pbdns) == 0: continue # Likely not running
                    thehostnames.append(pbdns)

            if len(thehostnames) == 0:
                print('')
                print('ERROR')
                print('----')
                print('')
                print('We did not find a host within the compute stack (we found {0})'.format(thehostnames))
                print('')
                input('Press Enter to leave ... ')
                return

            thehostname = random.choice(thehostnames)
            thessh = 'ssh -i ~/.ssh/ecs-login-{}-id_rsa -l ec2-user {}'.format(self.stage,thehostname)

            print('')
            print('----')
            cmd = '{0} uptime'.format(thessh, '{{.ID}}')
            print('Running on the ECS host ... to get rid of any SSH unknown host warnings:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            print('')
            print('----')
            cmd = '{0} docker ps --filter status=running --filter label=com.amazonaws.ecs.container-name=site-buildbarbuda --format {1} | sort --random-sort | head -n1'.format(thessh, '{{.ID}}')
            print('Finding a random site-buildbarbuda container on the ECS host:\n  {0}'.format(cmd))
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            webid = p.stdout.read().rstrip()
            drush = '{0} docker exec {1} runuser -u drupaladmin /home/drupaladmin/bin/drush'.format(thessh, webid)

            print('')
            print('----')
            print('Found Docker container id {0} for site-buildbarbuda'.format(webid))

            cmd = '{0} sql-query \'"DROP TABLE site_phase1"\''.format(drush)
            print('Running on the ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            cmd = '{0} sql-query \'"DROP TABLE site_phase2"\''.format(drush)
            print('Running on the ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            print('')
            print('----')
            print('')

            cmd = '{0} sql-query \'"SHOW TABLES"\' | grep -i ^site'.format(drush)
            print('Running on the ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            print('')
            input('Verify that you do NOT see site_phase* tables above. Then press Enter to proceed ... ')
        except:
            self.handle_menu_error()
            raise

    def promote_compute_stack(self, stack, all_compute_stacks, network, database):
        '''
        Follow the steps in site-buildbarbuda/docs/DESIGN-UPDATE.md

        Traffic is controlled by the ElasticLoadBalancer, and needs a corresponding setting in the AutoScalingGroup when machines get auto-replaced
        '''

        try:
            # find load balancer target groups for Redirect and Drupal
            cmd ='aws --profile site-{} --no-paginate --output json cloudformation describe-stacks --stack-name {}-network-{}'.format(self.stage, FLAVORSHORT, network)
            print(cmd)
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            jsonstr = p.stdout.read()
            output = json.loads(jsonstr)
            redirect_targetgroup = None
            drupal_targetgroup = None
            for s in output['Stacks']:
                for o in s['Outputs']:
                    if o['OutputKey'] == 'EcsLoadBalancerDrupalHttpsTargetGroup':
                        drupal_targetgroup = o['OutputValue']
                    if o['OutputKey'] == 'EcsLoadBalancerRedirectHttpTargetGroup':
                        redirect_targetgroup = o['OutputValue']
            if redirect_targetgroup is None: raise Exception('No Redirect load balancer target group')
            if drupal_targetgroup is None: raise Exception('No Drupal load balancer target group')

            # find all EC2 instances that share the Drupal database
            output = describe_instances(self.stage, network, database)

            # split into old and new hostname ... based on which compute stack they belong to
            oldhostnames = []
            newhostnames = []
            for r in output["Reservations"]:
                for i in r["Instances"]:
                    pbdns = i["PublicDnsName"]
                    if len(pbdns) == 0: continue # Likely not running

                    old = True
                    for t in i["Tags"]:
                        k = t["Key"]
                        v = t["Value"]
                        if k == "aws:cloudformation:stack-name" and v == stack:
                            old = False
                            break
                    if old:
                        oldhostnames.append(pbdns)
                    else:
                        newhostnames.append(pbdns)

            if len(oldhostnames) == 0:
                print('')
                print('WARNING')
                print('----')
                print('')
                print('We did not find an "old" host that is NOT IN the compute stack (we found {0})'.format(oldhostnames))
                print('It may mean that you are doing a first-time installation.')
                print('')
                input('Press Enter to continue ... ')

            if len(newhostnames) == 0:
                print('')
                print('ERROR')
                print('----')
                print('')
                print('We did not find a "new" host within the compute stack (we found {0})'.format(newhostnames))
                print('')
                input('Press Enter to leave ... ')
                return

            oldhostname = random.choice(oldhostnames) if len(oldhostnames) > 0 else None
            newhostname = random.choice(newhostnames) if len(newhostnames) > 0 else None
            oldssh = 'ssh -i ~/.ssh/ecs-login-{}-id_rsa -l ec2-user {}'.format(self.stage,oldhostname)
            newssh = 'ssh -i ~/.ssh/ecs-login-{}-id_rsa -l ec2-user {}'.format(self.stage,newhostname)
            oldsshinteractive = 'ssh -t -i ~/.ssh/ecs-login-{}-id_rsa -l ec2-user {}'.format(self.stage,oldhostname)
            newsshinteractive = 'ssh -t -i ~/.ssh/ecs-login-{}-id_rsa -l ec2-user {}'.format(self.stage,newhostname)

            all_cis = set()

            # find what we should bind for Drupal and Redirect family of tasks
            new_redirect_binds = acquire_compute_bindings(self.stage, stack, 'Redirect', all_cis)
            new_drupal_binds = acquire_compute_bindings(self.stage, stack, 'Drupal', all_cis)

            # find the old binds (the task bindings for all other stacks that share the network+database _except_ 'stack')
            old_stacks = {s for s in all_compute_stacks if s != stack and deconstruct_stack_name(s)[1] == network and deconstruct_stack_name(s)[2] == database}
            old_redirect_binds = set()
            old_drupal_binds = set()
            for old_stack in old_stacks:
                old_redirect_binds = old_redirect_binds | acquire_compute_bindings(self.stage, old_stack, 'Redirect', all_cis)
                old_drupal_binds = old_drupal_binds | acquire_compute_bindings(self.stage, old_stack, 'Drupal', all_cis)
            print('')
            print('Old stacks: ', old_stacks)
            print('New stack: ', stack)
            print('')
            print('Old Redirect bindings: ', old_redirect_binds)
            print('New Redirect bindings: ', new_redirect_binds)
            print('')
            print('Old Drupal bindings: ', old_drupal_binds)
            print('New Drupal bindings: ', new_drupal_binds)
            input('Press Enter to proceed ... ')

            new_cis = { b[0] for b in (new_redirect_binds | new_drupal_binds) }

            # resolve all the container instances for the new stack
            cmd ='aws --profile site-{} --no-paginate --output json ecs describe-container-instances --cluster {} --container-instances {}'.format(self.stage, stack, ' '.join(all_cis))
            print(cmd)
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            jsonstr = p.stdout.read()
            output = json.loads(jsonstr)
            failures = output['failures']
            reported_cis = output['containerInstances']

            # safety check
            for failure in failures:
                if failure['reason'] == 'MISSING':
                    ci = failure['arn']
                    if ci in new_cis:
                        raise Exception('Safety check failed. There is a new container instance {0} that is reported MISSING'.format(ci))

            # resolve all the container instances for the old stacks
            for old_stack in old_stacks:
                cmd ='aws --profile site-{} --no-paginate --output json ecs describe-container-instances --cluster {} --container-instances {}'.format(self.stage, old_stack, ' '.join(all_cis))
                print(cmd)
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                jsonstr = p.stdout.read()
                output = json.loads(jsonstr)
                failures.extend(output['failures'])
                reported_cis.extend(output['containerInstances'])

            # for old tasks (only) it is fine if their container instances are missing
            if len(reported_cis) != len(all_cis):
                raise Exception('Safety check failed. Saw {} reported container instances, but we asked for {} in total'.format( len(reported_cis), len(all_cis)))
            ci_ec2instance_map = dict()
            for ci in reported_cis:
                ci_ec2instance_map[ci['containerInstanceArn']] = ci['ec2InstanceId']

            print('')
            print('INSTRUCTIONS')
            print('----')
            print('1. You need the ECS private key in ~/.ssh/ecs-login-{}.id_rsa for the following commands to work'.format(self.stage))
            print('2. You need: chmod 600 ~/.ssh/ecs-login-{}-id_rsa'.format(self.stage))
            print('3. Your security group for the EC2 instances needs to allow access from this machine (try running: curl -s http://169.254.169.254/latest/meta-data/public-ipv4; echo) OR ssh will hang for a while')
            print('')
            if oldhostname is not None: print('We will be running commands on a random _old_ ECS host ({0})'.format(oldhostname))
            print('We will be running commands on a random _new_ ECS host ({0})'.format(newhostname))
            print('')
            print('WHAT WILL HAPPEN')
            print('----')
            print('')
            if oldhostname is not None:
                print('THEN. The Drupal site will be put into maintenance (from within the old Drupal services)')
                print('  * _Any_ Drupal service (old or new) will return a Site Maintenance Page and HTTP 503. ')
                print('  * Elastic Load Balancer (ELB) will put all HTTP 503 services (ex. Drupal, but not Redirect) into OutOfService')
                print('  * When all services in an ELB target group go OutOfService, ELB will send the request to a random service')
                print('  * The HTTP 503 is a signal to Google to stop indexing; https://webmasters.googleblog.com/2011/01/how-to-deal-with-planned-site-downtime.html')
                print('')
            print('THEN. Drupal update steps will be performed on the new Drupal services')
            print('THEN. The new Drupal and Redirect services will be added to ELB')
            if oldhostname is not None:
                print('THEN. The old Drupal and Redirect services will be removed from ELB')
            print('')
            input('Press Enter to proceed ... ')

            if oldhostname is not None:
                print('')
                print('----')
                cmd = '{0} uptime'.format(oldssh, '{{.ID}}')
                print('Running on the _old_ ECS host ... to get rid of any SSH unknown host warnings:\n  {0}'.format(cmd))
                subprocess.call (cmd, shell=True)

                print('')
                print('----')
                cmd = '{0} docker ps --filter status=running --filter label=com.amazonaws.ecs.container-name=site-buildbarbuda --format {1} | sort --random-sort | head -n1'.format(oldssh, '{{.ID}}')
                print('Finding a random site-buildbarbuda container on the _old_ ECS host:\n  {0}'.format(cmd))
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                webid = p.stdout.read().rstrip()
                drush = '{0} docker exec -it {1} runuser -u drupaladmin /home/drupaladmin/bin/drush'.format(oldsshinteractive, webid)

                print('')
                print('----')
                print('Found Docker container id {0} for old site-buildbarbuda'.format(webid))
                cmd = '{0} sset system.maintenance_mode 1'.format(drush)
                print('Running on the _old_ ECS host:\n  {0}'.format(cmd))
                subprocess.call (cmd, shell=True)

                print('')
                print('----')
                cmd = '{0} cache-rebuild'.format(drush)
                print('Running on the _old_ ECS host:\n  {0}'.format(cmd))
                subprocess.call (cmd, shell=True)

            print('')
            print('----')
            cmd = '{0} uptime'.format(newssh, '{{.ID}}')
            print('Running on the _new_ ECS host ... to get rid of any SSH unknown host warnings:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            print('')
            print('----')
            cmd = '{0} docker ps --filter status=running --filter label=com.amazonaws.ecs.container-name=site-buildbarbuda --format {1} | sort --random-sort | head -n1'.format(newssh, '{{.ID}}')
            print('Finding a random site-buildbarbuda container on the _new_ ECS host:\n  {0}'.format(cmd))
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            webid = p.stdout.read().rstrip()
            drush = '{0} docker exec -it {1} runuser -u drupaladmin /home/drupaladmin/bin/drush'.format(newsshinteractive, webid)

            print('')
            print('----')
            print('Found Docker container id {0} for new site-buildbarbuda'.format(webid))

            cmd = '{0} updatedb'.format(drush)
            print('Running on the _new_ ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            cmd = '{0} entity-updates'.format(drush)
            print('Running on the _new_ ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            cmd = '{0} core-requirements'.format(drush)
            print('Running on the _new_ ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            print('')
            print('')
            print(' ----------------------------------------- ')
            print('')
            print('')
            input('*Verify* the above worked. Press Enter to proceed ... ')

            # bind new Redirect
            targets = []
            for ci_port in new_redirect_binds:
                targets.append('Id={0},Port={1}'.format( ci_ec2instance_map[ci_port[0]], ci_port[1] ))
            cmd ='aws --profile site-{} --output text elbv2 register-targets --target-group-arn {} --targets {}'.format(self.stage, redirect_targetgroup, ' '.join(targets))
            print(cmd)
            subprocess.call (cmd, shell=True)

            # bind new Drupal
            targets = []
            for ci_port in new_drupal_binds:
                targets.append('Id={0},Port={1}'.format( ci_ec2instance_map[ci_port[0]], ci_port[1] ))
            cmd ='aws --profile site-{} --output text elbv2 register-targets --target-group-arn {} --targets {}'.format(self.stage, drupal_targetgroup, ' '.join(targets))
            print(cmd)
            subprocess.call (cmd, shell=True)

            # unbind old Redirect
            targets = []
            for (ci, port) in old_redirect_binds:
                if ci not in ci_ec2instance_map: continue
                targets.append('Id={0},Port={1}'.format( ci_ec2instance_map[ci], port ))
            if len(targets) > 0:
                cmd ='aws --profile site-{} --output text elbv2 deregister-targets --target-group-arn {} --targets {}'.format(self.stage, redirect_targetgroup, ' '.join(targets))
                print(cmd)
                subprocess.call (cmd, shell=True)

            # unbind old Drupal
            targets = []
            for (ci, port) in old_drupal_binds:
                if ci not in ci_ec2instance_map: continue
                targets.append('Id={0},Port={1}'.format( ci_ec2instance_map[ci], port ))
            if len(targets) > 0:
                cmd ='aws --profile site-{} --output text elbv2 deregister-targets --target-group-arn {} --targets {}'.format(self.stage, drupal_targetgroup, ' '.join(targets))
                print(cmd)
                subprocess.call (cmd, shell=True)

            # Finish bringing up the site
            # NOTE: The order (putting out of maintenance, and then cache-rebuild) seems backwards but
            # let's follow the order in https://www.drupal.org/docs/8/update/update-procedure-in-drupal-8
            # (perhaps cache-rebuild does more when out-of-maintenance)

            cmd = '{0} sset system.maintenance_mode 0'.format(drush)
            print('Running on the _new_ ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            cmd = '{0} cache-rebuild'.format(drush)
            print('Running on the _new_ ECS host:\n  {0}'.format(cmd))
            subprocess.call (cmd, shell=True)

            input('Press Enter to proceed ... ')
        except:
            self.handle_menu_error()
            raise

    def construct_parameters_menu(self, cloudparameters):
        submenu = CursesMenu("AWS CloudFormation Parameters")
        for key,val in sorted(cloudparameters.items()):
            # Skip over autogenerated parameters
            if key in autogen_params: continue
            # Otherwise show the option
            submenu.append_item(FunctionItem(key, self.change_param, [key]))
        return submenu

    def construct_stacks_menu(self, cloudparameters):
        submenu = CursesMenu("AWS CloudFormation Stacks")

        creates = []
        others = []

        if self.stacktype == 'network':
            creates.append(FunctionItem('Create new {0} stack'.format(self.stacktype), self.create_stack, [None, None]))

        # Find all the compute stacks except those truly dead ... even those that are in the middle of being deleted.
        # If the user wants to 'Promote', then we must make sure everything is removed from the load balancer except the
        # machines in the new stack
        all_compute_stacks = None
        if self.stacktype == 'compute':
            all_compute_stacks = set()
            for summ in list_stacks(self.stage):
                stack = summ["StackName"]
                status = summ["StackStatus"]

                # Truly dead?
                if status == "DELETE_COMPLETE": continue

                # split out type, network id and possibly database id
                (this_stacktype, this_network, this_database) = deconstruct_stack_name(stack)
                # skip non-buildbarbuda stacks
                if this_stacktype is None: continue
                # only want compute stacks
                if this_stacktype == 'compute': all_compute_stacks.add(stack)

        # We cannot update with the stacks in some states, so filter by status
        for summ in list_stacks(self.stage, 'CREATE_COMPLETE UPDATE_COMPLETE ROLLBACK_COMPLETE UPDATE_ROLLBACK_COMPLETE'):
            stack = summ["StackName"]
            status = summ["StackStatus"]
            ctime = summ["CreationTime"]
            descr = '{0} created {1}'.format(status, ctime)

            # split out type, network id and possibly database id
            (this_stacktype, this_network, this_database) = deconstruct_stack_name(stack)
            # skip non-buildbarbuda stacks
            if this_stacktype is None: continue

            # create menus for creating a child of an ancestor
            if (self.stacktype == 'database' and this_stacktype == 'network') or (self.stacktype == 'compute' and this_stacktype == 'database'):
                creates.append(FunctionItem('Create new {0} stack from: {1} ({2})'.format(self.stacktype, stack, descr), self.create_stack, [this_network, this_database]))

            # skip non-network if not network, etc.
            if self.stacktype != this_stacktype: continue

            others.append(FunctionItem('Create changeset for {0} stack: {1} ({2})'.format(self.stacktype, stack, descr), self.create_changeset_stack, [stack, this_network, this_database]))
            others.append(FunctionItem('Update {0} stack directly:      {1} ({2})'.format(self.stacktype, stack, descr), self.update_stack, [stack, this_network, this_database]))
            if self.stacktype == 'compute':
                others.append(FunctionItem('Mark {0} stack as good:         {1} ({2})'.format(self.stacktype, stack, descr), self.mark_compute_stack, [stack, this_network, this_database]))
                others.append(FunctionItem('Promote {0} stack:              {1} ({2})'.format(self.stacktype, stack, descr), self.promote_compute_stack, [stack, all_compute_stacks, this_network, this_database]))

        items = creates + others
        for item in items: submenu.append_item(item)
        return submenu

    def item_save(self):
        # go back to beginning of file
        self.preferencesfile.seek(0)
        # save the YAML
        yaml.dump(self.prefs, self.preferencesfile, default_flow_style=False)
        # make sure there is nothing left in the file after the YAML
        self.preferencesfile.truncate()
        self.preferencesfile.flush()

    def show(self):
        menu = CursesMenu("buildbarbuda.org AWS CloudFormation Main", show_exit_option = False)

        parameters_menu_item = SubmenuItem("AWS CloudFormation Parameters", submenu=self.parameters_menu)
        parameters_menu_item.set_menu(menu)

        stacks_menu_item = SubmenuItem("AWS CloudFormation Stacks", submenu=self.stacks_menu)
        stacks_menu_item.set_menu(menu)

        menu.append_item(parameters_menu_item)
        menu.append_item(stacks_menu_item)
        menu.append_item(FunctionItem("Save", self.item_save))
        menu.append_item(ExitItem("Exit without saving"))
        menu.show()

# main entry point

# Handle command line arguments
usage = 'usage: conf.py (dev|prod) network|database|compute'
if len(sys.argv) < 3:
  print(usage)
  sys.exit(1)
stage = sys.argv[1]
stacktype = sys.argv[2]
if stacktype not in ["network", "database", "compute"]:
  print(usage)
  sys.exit(1)

def main(stdscr):
    with open("cloudformation-{0}.yaml".format(stacktype), 'r') as cloudfile:
        cloudcfg = yaml.load(cloudfile)
        cloudparams = cloudcfg['Parameters']

        preferencesfilename = expanduser("~/.buildbarbuda.{0}.site-aws.yml".format(stage))
        with open(preferencesfilename, 'a'): # open for appending (so auto-create if necessary)
          pass
        with open(preferencesfilename, 'r+') as preferencesfile: # open for updating
          config = ConfigMenu(preferencesfile, stage, stacktype, cloudparams)
          config.show()

# be safe with curses terminal
wrapper(main)
