from __future__ import print_function
# Quick-and-dirty way to extract the Git commit hash
# Note this doesn't rely on any git packages being installed
# but it does need us to be in a git repository

from builtins import str
import nplab
import os, sys, platform

class GitFolderMissing(Exception):
    """Exception to be raised if the git folder is not found."""
    pass

def git_folder():
    """Find the git folder for the repo that contains nplab."""
    project_dir = os.path.dirname(os.path.dirname(nplab.__file__))
    git_folder = os.path.join(project_dir,'.git')
    if os.path.isdir(git_folder):
        return git_folder
    else:
        raise GitFolderMissing("Could not find the git folder - are you in develop mode?")

def current_branch():
    """Return the name of the current branch we're using"""
    f = open(os.path.join(git_folder(),'HEAD'), 'r')
    current_branch = f.read()[5:].strip()
    f.close()
    return current_branch

def latest_commit():
    """Find the SHA1 hash of the most recent commit."""
    #first, open the file with the SHA1 in it
    f = open(os.path.join(git_folder(), *(current_branch().split('/'))), 'r')
    sha1 = f.read().strip() #the file only contains the SHA1
    f.close()
    return sha1

def all_module_versions_string():
    """A string containing the version of all loaded modules with accessible version info."""
    modulestring = ""
    for m in list(sys.modules.values()):
        try:
            modulestring += m.__name__ + ": " + m.__version__ + "\n"
        except:
            pass
    return modulestring

def platform_string():
    """A string identifying the platform (OS, Python version, etc.)"""
    platform_info = ""
    for f in dir(platform):
        try:
            platform_info += f + ": " + str(getattr(platform, f)()) + "\n"
        except:
            pass
    return platform_info

def version_info_string():
    """Construct a big string with all avaliable version info."""
    version_string = "NPLab %s\n" % nplab.__version__
    try:
        version_string += "Branch: %s\n" % current_branch()
        version_string += "Commit: %s\n" % latest_commit()
    except GitFolderMissing:
        version_string += "Release version (not in a Git repository)\n"
    version_string += "\n"
    version_string += "Module versions:\n"
    version_string += all_module_versions_string()
    version_string += "\n"
    version_string += "Platform information:\n"
    version_string += platform_string()
    return version_string

if __name__ == '__main__':
    print(version_info_string())
