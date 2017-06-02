from netmiko import ConnectHandler
from netmiko import __version__ as netmiko_version
from napalm_base.base import NetworkDriver


class S300Driver(NetworkDriver):
    def __init__(self, hostname, username, password, timeout=60, optional_args=None):
        """NAPALM Cisco S300 Handler."""
        if optional_args is None:
            optional_args = {}
        self.hostname = hostname
        self.username = username
        self.password = password
        self.timeout = timeout
        
        netmiko_argument_map = {
            'port': None,
            'secret': '',
            'verbose': False,
            'global_delay_factor': 1,
            'use_keys': False,
            'key_file': None,
            'ssh_scrict': False,
            'system_host_keys': False,
            'alt_host_keys': False,
            'alt_key_file': '',
            'ssh_config_file': None
        }

        fields = netmiko_version.split('.')
        fields = [int(x) for x in fields]
        maj_ver, min_ver, bug_fix = fields
        if maj_ver >= 2:
            netmiko_argument_map['allow_agent'] = False
        elif maj_ver == 1 and min_ver >= 1:
            netmiko_argument_map['allow_agent'] = False

        self.netmiko_optional_args = {}
        for k, v in netmiko_argument_map.items():
            try:
                self.netmiko_optional_args[k] = optional_args[k]
            except KeyError:
                pass
        self.global_delay_factor = optional_args.get('global_delay_factor', 1)
        self.port = optional_args.get('port', 22)

        self.device = None
        self.profile = ['s300']

    def open(self):
        self.device = ConnectHandler(device_type='cisco_s300',
                                     host=self.hostname,
                                     username=self.username,
                                     password=self.password,
                                     **self.netmiko_optional_args)
        self.device.enable()

    def close(self):
        self.device.disconnect()

    def _send_command(self, command):
        """Wrapper for self.device.send.command().

        If command is a list will iterate through commands until valid command.
        """
        output = None
        if isinstance(command, list):
            for cmd in command:
                output = self.device.send_command(cmd)
                if "% Invalid" not in output:
                    break
        else:
            output = self.device.send_command(command)
        return output

    def get_config(self, retrieve='all'):
        configs = {
            'startup': '',
            'running': ''
        }

        if retrieve in ('startup', 'all'):
            command = 'show startup-config'
            output = self._send_command(command)
            configs['startup'] = output

        if retrieve in ('running', 'all'):
            command = 'show running-config'
            output = self._send_command(command)
            configs['running'] = output

        return configs
