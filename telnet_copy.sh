#!/usr/bin/expect
#
# Expect ftp wrapper
#
# ftp to/from system as user ftp

set timeout 10
set verbose 0
proc usage {} {
    puts "Transfer files using ftp"
    puts "usage: eftp [-v] get <system> <remote file> <local file>
    puts "       eftp [-v] put <system> <local file> <remote file>
    exit 1
}

if {[lindex $argv 0] == "-h" || [lindex $argv 0] == "-?"} {
    usage
}
if {[lindex $argv 0] == "-v"} {
    set verbose 1
}

set num_arg [expr [llength $argv] - $verbose]
if {$num_arg != 4} {
    usage
}

set cmd     [lindex $argv [expr $verbose + 0]]
set target  [lindex $argv [expr $verbose + 1]]
set file1   [lindex $argv [expr $verbose + 2]]
set file2   [lindex $argv [expr $verbose + 3]]

if {$cmd != "get" && $cmd != "put"} {
    puts "Invalid command"
    usage
}
if {$cmd == "put" && ![file exists $file1]} {
    puts "Source file $file1 doesn't exist"
    exit 1
}

exp_log_user 0
if {$cmd == "get"} {
    if {$verbose} {puts "Copying file from $target:$file1 to $file2"}
} else {
    if {$cmd == "put"} {
        if {$verbose} {puts "Copying file from $file1 to $target:$file2"}
    } else {
        puts "Invalid command"
        if {$verbose} { usage }
        exit 1
    }
}

set ftp_result 0
spawn ftp $target
set timeout 2
expect {
    "Name ($target:admin):" {
    }
    timeout {
        puts "Error connecting to $target"
        exit 1
    }
}
send -- "ftp\r"
expect "Password:"
send -- "ftp\r"        # change to your password
expect "ftp> "
send -- "binary\r"
expect "ftp> "
send -- "prompt\r"
expect "ftp> "
set timeout 40

send "$cmd $file1 $file2 \r"
expect {
    "227 Entering Passive Mode" {
        if {$verbose} { puts "Start transfer" }
    }
    "local: $file1: No such file or directory" {
        puts "Local file $file1 is missing"
        set ftp_result 1
    }
    timeout {
        puts "timeout on start"
        set ftp_result 1
    }
}

expect {
    "150 Opening BINARY mode data connection" {
    }
    -re {(\d+\s)(.*\n)} {
        puts "ftp error occurred: '$expect_out(1,string) [string trim $expect_out(2,string)]'"
        set ftp_result 1
    }
    timeout {
        #puts "timeout2"
        set ftp_result 1
    }
}

if {0 == $ftp_result} {
    expect {
         "226 Transfer complete." {
             if {$verbose} { puts "Transfer complete" }
         }
         timeout {
             #puts "timeout2"
             set ftp_result 1
         }
    }
}

expect "ftp> "
send "quit\r"
expect "Goodbye."

exp_wait
if {$verbose} { puts "Result $ftp_result" }
exit  $ftp_result
