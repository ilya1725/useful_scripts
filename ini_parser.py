#!/usr/bin/env python

"""
Created on Sat Aug 08 15:58:20 2015

@author: Ilya Katsnelson

 Simple INI file processor. It will read specified INI file or create one from data.

 Syntax:
 1. String starting from '//', '#', or ';' are concidered comments.
 2. Sections are denoted by []
 3. The data is store in 'key'='value' pairs

"""
import sys, os, re
import traceback
import platform

# ini file exception
class iniException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# ini file class
class ini_data:
    '''
    INI data storage object
    _data dictionary of sections and comments
    {_comment} -> [...]
    {section} -> {name, value}[_comment]
    '''

    # Global constants
    _comment_key = "_comment"
    _comment_head = '#'

    # Dictionary of all INI entries
    _data = None

    def __init__(self, file_name=None):
        self._data = dict()
        if (None != file_name):
            self.parse(file_name, False)

    def __str__(self):
        output = ""
        if (len(self._data) != 0):
            # print the data in proper INI format
            ini_int_data = self._data

            # print the global comment
            if (ini_int_data.has_key(self._comment_key) == True):
                for comment in ini_int_data[self._comment_key]:
                    output += ("%s %s\n" % (self._comment_head, comment))
                output += "\n"

            for section in ini_int_data:
                if (section != self._comment_key):
                    output += ("[%s]\n" % (section))
                    section_dict = ini_int_data[section]

                    # print the section comment
                    if (section_dict.has_key(self._comment_key) == True):
                        for comment in section_dict[self._comment_key]:
                            output += ("%s %s\n" % (self._comment_head, comment))

                    for key in section_dict:
                        if (key != self._comment_key):
                            output += ("%s=%s\n" % (key, section_dict[key]))

                    output += "\n"

            return output
        else:
            return output

    def parse(self, file_name, clear=True):
        '''
        Process the passed INI file and populate the internal structure
        '''
        status = True;
        if (clear == True):
            self._data.clear();

        try:
            if (os.path.isfile(file_name) == False):
                print ("ERROR: ini file '%s' doesn't exist\n" % file_name);
                return False;
            else:
                ini_file = open(file_name);
                ini_int_data = self._data;
                global_scope = True;

                for ini_line in ini_file:
                    # skip the empty lines
                    if (len(ini_line) == 0):
                        continue

                    ini_line = ini_line.strip()

                    # Find if the line is a comment - starts from ;, #, //
                    matchObj = re.match(r'^([#;]|/{2})(.*)', ini_line);
                    if (None != matchObj):
                        if (ini_int_data.has_key(self._comment_key) == False):
                            ini_int_data[self._comment_key] = []
                        ini_int_data[self._comment_key].append(matchObj.group(2));

                        continue

                    # Find if the line is a section in []
                    matchObj = re.match(r'^\[(.*)\]', ini_line)
                    if (None != matchObj):
                        if (ini_int_data.has_key(matchObj.group(1)) == True):
                            raise Exception("Duplicate section %s" % matchObj.group(1));
                        else:
                            # Create local dictionary for this section
                            if (global_scope == True):
                                global_scope = False
                            else:
                                ini_int_data = self._data

                            ini_int_data[matchObj.group(1)] = dict()
                            ini_int_data = ini_int_data[matchObj.group(1)]

                        continue

                    # Find if the line is some data. Error if not in a section.
                    matchObj = re.match(r'^(.+)=(.*)', ini_line);
                    if (None != matchObj):
                        if (ini_int_data.has_key(matchObj.group(1)) == True):
                            raise Exception("Duplicate key %s" % matchObj.group(1));
                        else:
                            # Add the key+values
                            ini_int_data[matchObj.group(1).strip()] = matchObj.group(2).strip();

        except KeyError, e:
            print ("Error: %s" % e)
            status = False
        except IOError, e:
            print ("IOError: %s\n" % sys.exc_info()[1])
            traceback.print_exc(file = sys.stdout)
            status = False
        except:
            print ("Unexpected error: %s\n" % sys.exc_info()[1])
            traceback.print_exc(file = sys.stdout)
            status = False

        return status

    def add_comment(self, comment, section=None):
        '''
        Add comment string to the specified section,
        or the global scope if not specifed
        '''
        ini_int_data = self._data
        if (section != None):
            if (ini_int_data.has_key(section) == False):
                ini_int_data[section] = dict()

            ini_int_data = ini_int_data[section]

        # Find if there are any comment sections
        if (ini_int_data.has_key(self._comment_key) == False):
            ini_int_data[self._comment_key] = []

        comment_lines = comment.splitlines();
        comment_list = ini_int_data[self._comment_key]
        for line in comment_lines:
            comment_list.append(line)

        ini_int_data[self._comment_key] = comment_list

        return True

    def add_data(self, section, key=None, value=None):
        '''
        Add key+value pair to the specified section.
        Create section if it doesn't exist.
        '''
        ini_int_data = self._data
        if (ini_int_data.has_key(section) == False):
            ini_int_data[section] = dict()

        # Exit if we only want to add a section
        if (key == None):
            return True

        ini_int_data = ini_int_data[section]

        # Find duplicates
        if (ini_int_data.has_key(key) == True):
            raise iniException("Error: key '%s' already exist." % key)

        # Find if there are any comment sections
        ini_int_data[key] = value

        return True

    def get_data(self, section, key=None):
        '''
        Get value for the specified key from key+value pair to the specified section.
        Get the list of key+value tuples from the specified section if key is None.
        Return value or list. Throw iniException in case of the error
        '''
        ini_int_data = self._data
        if (ini_int_data.has_key(section) == False):
            raise iniException ("Error: section '%s' doesn't exist." % section)

        ini_int_data = ini_int_data[section]

        # Find the values
        if (key != None):
            # return the value
            if (ini_int_data.has_key(key) == False):
                raise iniException ("Error: key '%s' doesn't exist." % key)
    
            # Find if there are any comment sections
            return (ini_int_data[key])
        else:
            # return the list of key+values
            results = []
            for key in ini_int_data:
                if (key != self._comment_key):
                    results.append((key, ini_int_data[key]))
            return results

    def is_data(self, section, key):
        '''
        Return true if the specified key exist in the specified section
        '''
        ini_int_data = self._data
        if (ini_int_data.has_key(section) == False):
            return False

        # Find the values
        if (ini_int_data[section].has_key(key) == False):
            return False

        return True

###############################################################################
def main():
    print("Autotesting of the ini parcer.\n")

    options = ini_data('C:\Users\ilya\mercurial.ini')
    print options
    print ("%s" % '-'*40)

    opts = ini_data();
    opts.add_comment("Simple testing code.\nVersion 1")
    opts.add_data('header','version',1)

    print("Check the error reporting.")
    print("Adding duplicate value")
    try:
        opts.add_data('header','version',2)
    except iniException, e:
        print ("Error: %s" % e)
        print("Error adding duplicate!")

    # More data to actually create something intersting
    opts.add_data('system info')
    opts.add_comment('more information about the system', 'system info')
    opts.add_data('system info', 'machine', platform.machine())
    opts.add_data('system info', 'java_ver', platform.java_ver())
    opts.add_data('system info', 'processor', platform.processor())
    opts.add_data('system info', 'python_version', platform.python_version())

    print("Get the values back")
    print("Version: %s\n" % opts.get_data('header', 'version'))

    print("Get the values back 2")
    for b in opts.get_data('system info'):
        key, val = b
        print("%s-%s" % (key, val))
    
    print ("%s" % '-'*40)
    print opts

###############################################################################
if __name__ == "__main__":
    main()

