#!/usr/bin/env python
import sys
from os.path import expanduser

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
    return { 'Sub' : value }
def getatt_constructor(loader, node):
    value = loader.construct_scalar(node)
    return { 'GetAtt' : value }
yaml.add_constructor(u'!Ref', ref_constructor)
yaml.add_constructor(u'!Sub', sub_constructor)
yaml.add_constructor(u'!GetAtt', getatt_constructor)

class ConfigMenu:
    """
    Configuration menu
    """

    def __init__(self, ymlfile, cloudparameters):
        self.cfg = yaml.safe_load(ymlfile)
        if self.cfg is None:
            self.cfg = {'Parameters': dict()}
        self.ymlfile = ymlfile
        self.parameters_menu = self.construct_parameters_menu(cloudparameters)

    def hi():
        pass

    def construct_parameters_menu(self, cloudparameters):
        submenu = CursesMenu("AWS CloudFormation Parameters")
        for key,val in cloudparameters.items():
            if key not in self.cfg['Parameters'] and 'Default' in val:
                self.cfg['Parameters'][key] = val['Default']
            submenu.append_item(FunctionItem(key, self.hi))
        return submenu

    def item_save(self):
        # go back to beginning of file
        ymlfile.seek(0)
        # save the YAML
        yaml.dump(self.cfg, ymlfile, default_flow_style=False)
        # make sure there is nothing left in the file after the YAML
        ymlfile.truncate()
        ymlfile.flush()

    def show(self):
        menu = CursesMenu("plainlychrist.org AWS CloudFormation Main", show_exit_option = False)

        parameters_menu_item = SubmenuItem("Show AWS CloudFormation Parameters", submenu=self.parameters_menu)
        parameters_menu_item.set_menu(menu)

        menu.append_item(parameters_menu_item)
        menu.append_item(FunctionItem("Save", self.item_save))
        menu.append_item(ExitItem("Exit without saving"))
        menu.show()

# main entry point
with open("cloudformation.yaml", 'r') as cloudfile:
    cloudcfg = yaml.load(cloudfile)
    cloudparameters = cloudcfg['Parameters']

    configfile = expanduser("~/.plainlychrist.site-aws.yml")
    with open(configfile, 'a'): # open for appending (so auto-create if necessary)
        pass
    with open(configfile, 'r+b') as ymlfile: # open for updating in binary mode
        config = ConfigMenu(ymlfile, cloudparameters)
        config.show()
