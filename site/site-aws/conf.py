#!/usr/bin/env python3
# vim: autoindent smarttab tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=python
import sys
import readline
from os.path import expanduser
import subprocess
from datetime import datetime
import re
import random
import base64
import os

# import a text menu library
try:
    from cursesmenu import CursesMenu
    from cursesmenu.items import FunctionItem, SubmenuItem, CommandItem, ExitItem
except ImportError as e:
    print ("FATAL: %s. Please follow the installation instructions at http://curses-menu.readthedocs.io/en/latest/installation.html" % (e))
    sys.exit(1)

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

class ConfigMenu:
    """
    Configuration menu
    """

    def __init__(self, preferencesfile, stacktype, cloudparams):
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

    def form_params(self):
        s = ''
        for key in self.prefs['Parameters']:
            # Not all of our preferences are usable by this CloudFormation template
            if key not in self.templatekeys: continue
            # We'll do ModificationTimestamp and NetworkIdFromDatabaseId just below
            if key in ['ModificationTimestamp', 'NetworkIdFromDatabaseId']: continue

            p = self.prefs['Parameters'][key]
            if 'CommaDelimitedList' == self.prefs['Types'][key]:
                p = p.replace(',', '\,')
            s += " ParameterKey=%s,ParameterValue='%s'" % (key, p)

        # Make ModificationTimestamp like 20170129T013016370623
        modts = datetime.utcnow().isoformat('T').translate(str.maketrans('', '', ':-.'))
        s += " ParameterKey=ModificationTimestamp,ParameterValue='%s'" % (modts,)

        # If we have DatabaseId=123-456, then produce NetworkIdFromDatabaseId=123
        if self.stacktype == 'compute' and 'DatabaseId' in self.prefs['Parameters']:
            dbid = self.prefs['Parameters']['DatabaseId']
            (nid, did) = dbid.split('-')
            s += " ParameterKey=NetworkIdFromDatabaseId,ParameterValue='{0}'".format(nid)
        return s

    def create_stack(self):
        s = 'aws --profile site-dev cloudformation create-stack --parameters'
        s += self.form_params()
        has_network = 'NetworkId' in self.prefs['Parameters']
        has_database = 'DatabaseId' in self.prefs['Parameters']
        if self.stacktype == 'network':
            ident = '{0:05d}'.format(random.randrange(0,100000))
        elif self.stacktype == 'database' and has_network:
            ident = '{0}-{1:05d}'.format(self.prefs['Parameters']['NetworkId'], random.randrange(0,100000))
        elif self.stacktype == 'compute' and has_database:
            ident = '{0}-{1:05d}'.format(self.prefs['Parameters']['DatabaseId'], random.randrange(0,100000))
        else:
            # This comes when NetworkId or DatabaseId is not set ... cloudformation will complain with nice error message
            ident = '{0:05d}-MISSING'.format(random.randrange(0,100000))
        s += " --stack-name 'plainlychrist-{0}-{1}'".format(self.stacktype, ident)
        s += ' --template-body "$(cat cloudformation-{0}.yaml)"'.format(self.stacktype)
        print(s)
        subprocess.call (s, shell=True)
        input('Press Enter to continue ... ')

    def create_changeset_stack(self, stack):
        changets = datetime.utcnow().isoformat('T').translate(str.maketrans('', '', ':-.'))
        s = 'aws --profile site-dev cloudformation create-change-set --parameters'
        s += self.form_params()
        s += " --stack-name '{0}'".format(stack)
        s += " --change-set-name '{0}-{1}'".format(stack, changets)
        s += ' --template-body "$(cat cloudformation-{0}.yaml)"'.format(self.stacktype)
        print(s)
        subprocess.call (s, shell=True)
        input('Press Enter to continue ... ')

    def update_stack(self, stack):
        s = 'aws --profile site-dev cloudformation update-stack --parameters'
        s += self.form_params()
        s += " --stack-name '{0}'".format(stack)
        s += ' --template-body "$(cat cloudformation-{0}.yaml)"'.format(self.stacktype)
        print(s)
        subprocess.call (s, shell=True)
        input('Press Enter to continue ... ')

    def construct_parameters_menu(self, cloudparameters):
        submenu = CursesMenu("AWS CloudFormation Parameters")
        for key,val in sorted(cloudparameters.items()):
            submenu.append_item(FunctionItem(key, self.change_param, [key]))
        return submenu

    def construct_stacks_menu(self, cloudparameters):
        submenu = CursesMenu("AWS CloudFormation Stacks")

        submenu.append_item(FunctionItem('Create new {0} stack'.format(self.stacktype), self.create_stack, []))

        p = subprocess.Popen('aws --profile site-dev cloudformation list-stacks', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        for line in p.stdout.readlines():
            (a,b,c,d,arn,stack,status,h) = line.split("\t")

            # We cannot update with the stacks in this state
            if status.startswith("CREATE_IN_PROGRESS"): continue
            if status.startswith("DELETE"): continue
            if status.startswith("ROLLBACK_COMPLETE"): continue

            m = re.match('plainlychrist-([a-z]+)-[0-9]+', stack)
            if m is None: continue
            that_stacktype = m.group(1)
            if self.stacktype != that_stacktype: continue

            submenu.append_item(FunctionItem('Create changeset for {0} stack: {1}.'.format(self.stacktype, stack), self.create_changeset_stack, [stack]))
            submenu.append_item(FunctionItem('Update {0} stack directly: {1}.'.format(self.stacktype, stack), self.update_stack, [stack]))
        return submenu

    def item_save(self):
        # go back to beginning of file
        preferencesfile.seek(0)
        # save the YAML
        yaml.dump(self.prefs, preferencesfile, default_flow_style=False)
        # make sure there is nothing left in the file after the YAML
        preferencesfile.truncate()
        preferencesfile.flush()

    def show(self):
        menu = CursesMenu("plainlychrist.org AWS CloudFormation Main", show_exit_option = False)

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
usage = 'usage: conf.py network|database|compute'
if len(sys.argv) < 2:
  print(usage)
  sys.exit(1)
stacktype = sys.argv[1]
if stacktype not in ["network", "database", "compute"]:
  print(usage)
  sys.exit(1)

with open("cloudformation-{0}.yaml".format(stacktype), 'r') as cloudfile:
    cloudcfg = yaml.load(cloudfile)
    cloudparams = cloudcfg['Parameters']

    preferencesfilename = expanduser("~/.plainlychrist.site-aws.yml")
    with open(preferencesfilename, 'a'): # open for appending (so auto-create if necessary)
      pass
    with open(preferencesfilename, 'r+') as preferencesfile: # open for updating
      config = ConfigMenu(preferencesfile, stacktype, cloudparams)
      config.show()
