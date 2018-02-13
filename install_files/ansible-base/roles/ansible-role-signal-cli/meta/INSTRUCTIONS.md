Four (4) must be defined in either `securedrop-staging.yml` or `install_files/ansible-base/group_vars/all/site-specific`

- `signal_notifications` (default is false) must be set to `True` (e.g.: `signal_notifications: True`)
- `The signal number which will be used to send alerts (e.g.: `signal_number: "+15555555"`)
- `signal_cli_copy_config`: which will specify if the config at install_files/ansible-base/+15555555 will be copied over to the server (e.g. `signal_cli_copy_config: False`)
- `signal_destination_number`: The number which will receive the signal notifications (e.g.: `signal_destination_number: "+15555556666"`)

If you would like to set up your SecureDrop instance to send Signal messages, here are the steps you must take:

1- Acquire a phone number (VoIP service, a SIM card from a phone provider and temporarily use it on your phone). Ensure that you remain in control of this number, as an attacker could re-register that number and intercept OSSEC messages coming from your server
2- Set `signal_notifications: True`, `signal_cli_copy_config: False` and specify the values of `signal_number` and `signal_destination_number`
3- If you already have a signal config for a number or if you are restoring from a backup, move it to `install_files/ansible-base`, set `signal_cli_copy_config: True` and go to step X
4- Run the install script (`securedrop-admin install`)
5- If you have copied your signal config, you should be receiving signal messages Otherwise, please continue
6- If you have not run `securedrop-admin tailsconfig`, do it now
7- SSH into the monitor server (`ssh mon`)
8- sudo -u ossec bash -c 'signal-cli --config /etc/signal/data/ -u +15143121553 register -v'
9- sudo -u ossec bash -c 'signal-cli --config /etc/signal/data/ -u +15143121553 verify <NUMBER>'
SCP the configuration back to you workstation for safeguarding purposes. Exercise great caution as the configuration file will contain encryption keys.
10 -if you are in an ssh session `exit` until you are back in `/Persistent/securedrop`
ssh -i ~/.vagrant.d/insecure_private_key vagrant@192.168.121.218 'sudo cat /etc/signal/data/+15143121553' > install_files/ansible-base/+15143121553

12 - Run `securedrop-admin install` again if you would like to receive notifications