# Quick-and-dirty way to extract the Git commit hash
# Note this doesn't rely on any git packages being installed
# but it does need us to be in a git repository

import nplab
import os, sys

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

if __name__ == '__main__':
    print "Current branch: " + os.path.join(git_folder(),*(current_branch().split('/')))
    print "Current commit: " + latest_commit()

