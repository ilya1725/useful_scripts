#!/usr/bin/env python

"""
    System control script.
    This script allows users to change different parameters of the local/remote server.
    It uses available utilities such as iDRAC or others.

    General options:
        -d, --dry-run: Don't execute, show the rules.
        -V, --version: Print the version of the script.
        -v, --verbose: Generate verbose output.
        -c, --command: Command to run on RACADM

"""

import os
import pexpect
import re
import syslog
import time
import subprocess

import optparse

###############################################################################
VER_STRING                  = "0.1"
VM_PAT_LINUX_PROMPT         = re.compile(r'(?!^\s)^.*[#\$]$|(?!^\s)^.*[#\$]\s$|(?!^\s)^[#\$]\s$|(?!^\s)\[.*\][#\$]|\[.+@.+\][#\$]|/.+->\s',re.M)

###############################################################################
def filterPick(lines, regex_str):
    """
    Remove from the list of strings string that match the supplied regex string
    """
    regex = re.compile(r'%s' % regex_str)
    return [i for i in lines if not regex.match(i)]

###############################################################################
class CaptureResult( object ):
    """class returned by function subprocess_capture() which is a wrapper around Popen"""

    def __init__(self, out, err, rc):
        self.out = out
        self.err = err
        self.returncode = rc

    def __nonzero__(self):
        """ True means good/success (i.e., 0). """
        return self.returncode == 0

def subprocess_capture(command, shell=False):
    """Execute a subprocess, catching output and subprocess exception.
       Returns a CaptureResult object of stdout, stderr, and returncode
    """

    try:
        subproc = subprocess.Popen(
            command, shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        pass

    result = subproc.communicate()
    return CaptureResult(result[0], result[1], subproc.returncode)

###############################################################################
class CleanFile(file):
    """
    Subclass of file object to avoid recording extensive whitespace characters
    """
    def write(self, text):
        # Remove the whitespaces
        out_text = ''
        # process the backspace properly
        bline = ''
        for c in text:
            if (ord(c) == 0x8):
                if (len(bline) == 0):
                    # Move the file pointer.
                    file.seek(self, -1, os.SEEK_CUR)
                else:
                    bline = bline[:-1]
            else:
                bline += c

        # remove whitespaces from inside a line
        out_text += ''.join(c for c in bline if (ord(c) >= 32 or ord(c) == 10))

        file.write(self, out_text)

###############################################################################
class RacAdm(object):
    """Main class which abstracts communication with a RACADM utility.
    """

    def __init__(self, rac_system='',
                 rac_system_user='',
                 rac_system_passwd='',
                 file_log_out=None):
        self.system = rac_system
        self.user = rac_system_user
        self.user_passwd = rac_system_passwd
        self.local = False
        self.error = ""
        self.fout = file_log_out

        if (rac_system == ''):
            self.local = True

    @property
    def system(self):
        """System to connect to. Empty if local"""
        return self.system

    @property
    def user(self):
        """Username for the system to connect to. Empty if local"""
        return self.user

    @property
    def error(self):
        """Return error string """
        return self.error

    def get_version(self):
        """
        Return the RACADM version information
        """
        return self.__execute_cmd__('racadm getversion')

    def is_error(self):
        """
        Return flag indicating if the last command resulted in an error
        """
        if (self.error != ''):
            return True
        return False

    def __execute_cmd__(self, command):
        '''
        Just run a simple command depending on the location - remote or local
        '''
        output = ""
        full_command = 'racadm %s' % command
        self.error = ''

        try:

            if (self.local):
                p = pexpect.spawn ("racadm %s'" % (command))
                p.setecho(True)
                p.logfile_read = self.fout

                j = p.expect ([pexpect.EOF, pexpect.TIMEOUT, 'Error'], timeout=120)
                if (j != 0):
                    raise Exception ("Error running command '%s' [%d]" % (full_command, j))

                output = p.before

            else:
                # In order to prevent some extra window popping up asking for password,
                # clear the two terminal variables. Check the SSH man page for the reason
                os.environ["SSH_ASKPASS"] = ''
                os.environ["DISPLAY"] = ''

                p = pexpect.spawn ("ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %s@%s 'racadm %s'" %
                                    (self.user, self.system, command))
                p.setecho(True)
                p.logfile_read = self.fout
                time.sleep (30)

                i = p.expect (["%s@%s's password:" % (self.user, self.system), pexpect.EOF, pexpect.TIMEOUT, 'Error'], timeout=60)
                if (i == 0):
                    p.send(self.user_passwd + '\n')
                    j = p.expect ([pexpect.EOF, pexpect.TIMEOUT, 'Error'], timeout=120)
                    if (j != 0):
                        raise Exception ("Error running command '%s' on system %s@%s [%d]" % (full_command, self.user, self.system, j))

                    output = p.before

                else:
                    raise ("Error executing command '%s' at remote RACADM at %s [%d]" % (full_command, self.system, i))

                # Process the output
                if (len(output) > 0):
                    # Sometimes there is a line complaining about some home directory
                    output_lines = output.splitlines()
                    output_lines = filterPick(output_lines, "^Could not chdir to home directory.+")

                    output = "\n".join(output_lines)

        except Exception, e:
            print ("execute exception: %s\n" % e)
        finally:
            p.close()

        return output


###############################################################################
def main():

    parser = optparse.OptionParser(usage="usage: %prog [options]")
    parser.add_option("-d", "--dry-run",action="store_true",dest="dry_run",
        help="Flag to indicate to just run the code without any device access")
    parser.add_option("-V", "--version",action="store_true",dest="script_version",
        help="Print script version and exit")
    parser.add_option("-v", "--verbose",action="store_true",dest="verbose",
        help="Provide more verbose output")
    parser.add_option("-l", "--log-file",type="string",dest="log_file",
        help="File to store all the logging in",
        default=None)
    parser.add_option("-s", "--remote-system",type="string",dest="remote_system",
        help="System name where RACADM resides",
        default=None)
    parser.add_option("-u", "--remote-system-user",type="string",dest="remote_system_user",
        help="User name at the system where RACADM resides",
        default=None)
    parser.add_option("-p", "--remote-system-passwd",type="string",dest="remote_system_passwd",
        help="Password for the user name at the system where RACADM resides",
        default=None)
    parser.add_option("-c", "--command",type="string",dest="racadm_cmd",
        help="Command to run on RACADM",
        default=None)

    (options, args) = parser.parse_args()

    if (options.script_version):
        print ("Script version: %s" % VER_STRING)
        return 0

    fout = None
    if (options.log_file != None):
        fout = CleanFile (options.log_file, 'w')

    racadm = RacAdm(options.remote_system, options.remote_system_user, options.remote_system_passwd, fout)
    output = racadm.__execute_cmd__(options.racadm_cmd)

    print output

    if (racadm.is_error()):
        return 1

    return 0

if __name__ == '__main__':
    main()
