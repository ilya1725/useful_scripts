#!/usr/bin/expect -f

# Simple expect script to automate the ssh connections to remote systems
# It will open the ssh shell, with user and password, and setup the environment

set prompt "root@.~# "

# connect via ssh
spawn ssh -p 102 user@<system>

#######################
expect {
  -re ".*es.*o.*" {
    exp_send "yes\r"
    exp_continue
  }
  -re ".*sword.*" {
    exp_send "<enter_passowrd>\r"
  }
}

sleep 1
send "alias ll=\"ls -al --color\"\r"

interact
