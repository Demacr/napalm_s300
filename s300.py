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

    @staticmethod
    def _parse_uptime(uptime_str):
        uptime_str = uptime_str.strip()
        days, hms = uptime_str.split(',') # 45,23:02:04
        hours, minutes, seconds = hms.split(':')
        days = int(days)
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        return days * 86400 + hours * 3600 + minutes * 60 + seconds

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

    def get_facts(self):
        vendor = u'Cisco'
        uptime = -1
        serial_number, fqdn, os_version, hostname, model = (u'Unknown', u'Unknown', u'Unknown', u'Unknown', u'Unknown')

        show_system = self._send_command('show system')
        show_system_id = self._send_command('show system id')
        show_version = self._send_command('show version')
        show_hosts = self._send_command('show hosts')
        show_ip_int = self._send_command('show ip interface')

        # uptime / hostname / model
        for line in show_system.splitlines():
            if 'System Up Time' in line:
                _, uptime_str = line.split(':sec):')
                uptime = self._parse_uptime(uptime_str)
            if 'System Name:' in line:
                hostname = line.split('Name:')[-1].strip()
            if 'System Description' in line:
                model = line.split(':')[1].strip().split(' ')[0]

        # Serail number
        _, serial_number = show_system_id.split(': ')

        # OS version
        # >SW version    1.4.5.02 ( date  20-Apr-2016 time  12:22:49 )\
        for line in show_version.splitlines():
            if 'SW version' in line:
                os_version = line.split(' (')[0].split('version')[1].strip()

        return {
            'uptime': uptime,
            'vendor': vendor,
            'hostname': hostname,
            'serial_number': serial_number,
            'os_version': os_version,
            'model': model
        }
