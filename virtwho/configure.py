import os
from virtwho.settings import Configure
from virtwho.settings import config
from virtwho.settings import TEMP_DIR
from virtwho.ssh import SSHConnect
from virtwho.base import hostname_get


class VirtwhoHypervisorConfig:
    """Able to create and manage /etc/virt-who.d/xxx.conf file when
    call this class"""

    def __init__(self, mode='esx', register_type='rhsm'):
        """Create virt-who configuration file with basic options. All
        data come from virtwho.ini. All local files are backed up
        to /temp directory of the project root.
        :param mode: The hypervisor mode.
            (esx, xen, hyperv, rhevm, libvirt, kubevirt, ahv, local)
        :param register_type: The subscription server. (rhsm, satellite)
        """
        self.mode = mode
        self.section = f'virtwho-{self.mode}'
        self.register = get_register_handler(register_type)
        self.hypervisor = get_hypervisor_handler(mode)
        self.remote_ssh = virtwho_ssh_connect(mode)
        if not os.path.exists(TEMP_DIR):
            os.mkdir(TEMP_DIR)
        self.local_file = os.path.join(TEMP_DIR, f'{mode}.conf')
        self.remote_file = f'/etc/virt-who.d/{mode}.conf'
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)

    def create(self):
        """create virt-who config file under /etc/virt-who.d/.
        """
        if self.mode == 'local':
            self.update('type', 'libvirt')
        else:
            self.update('type', self.mode)
            self.update('hypervisor_id', 'hostname')
        if self.mode == 'kubevirt':
            self.update('kubeconfig', self.hypervisor.config_file)
        if self.mode in ('esx', 'xen', 'hyperv', 'rhevm', 'libvirt', 'ahv'):
            if self.mode == 'rhevm':
                ssh_rhevm = SSHConnect(host=self.hypervisor.server,
                                       user=self.hypervisor.ssh_username,
                                       pwd=self.hypervisor.ssh_password)
                self.hypervisor.server = f'''https://{hostname_get(ssh_rhevm)}:
                                             443/ovirt-engine'''
            self.update('server', self.hypervisor.server)
            self.update('username', self.hypervisor.username)
            self.update('password', self.hypervisor.password)
        self.update('rhsm_hostname', self.register.server)
        self.update('rhsm_username', self.register.username)
        self.update('rhsm_password', self.register.password)
        self.update('rhsm_prefix', self.register.prefix)
        self.update('rhsm_port', self.register.port)
        self.update('owner', self.register.default_org)

    def update(self, option, value):
        """Add or update an option
        :param option: Option will be added if not exist.
        :param value: Value to update for the option.
        """
        self.cfg.update(self.section, option, value)

    def delete(self, option):
        """Delete an option
        :param option: Option to remove.
        """
        self.cfg.delete(self.section, option)

    def destroy(self):
        """Remove both the local and remote files"""
        os.remove(self.local_file)
        self.remote_ssh.remove_file(self.remote_file)


class VirtwhoGlobalConfig:
    """Able to manage /etc/virt-who.conf file when call this class"""

    def __init__(self, mode=None):
        """virt-who.conf file is backed up to /temp directory of the
        project root.
        :param mode: Hypervisor mode. When mode is local, will manage
            the local libvirt host, othervise will manage the host for
            all other remote modes.
        """
        self.mode = mode
        self.remote_ssh = virtwho_ssh_connect(self.mode)
        if not os.path.exists(TEMP_DIR):
            os.mkdir(TEMP_DIR)
        self.local_file = os.path.join(TEMP_DIR, 'virt-who.conf')
        self.remote_file = '/etc/virt-who.conf'
        self.save_file = os.path.join(TEMP_DIR, 'virt-who.conf.save')
        if not os.path.exists(self.save_file):
            self.remote_ssh.get_file(self.remote_file, self.save_file)
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)

    def update(self, section, option, value):
        """Add section, add option or update option
        :param section: Section will be added if not exist.
        :param option: Option will be added if not exist.
        :param value: Value to update for the option.
        """
        self.cfg.update(section, option, value)

    def delete(self, section, option=None):
        """Remove a section or option
        :param section: Section will be removed when no option provided.
        :param option: Option to remove.
        """
        self.cfg.delete(section, option)

    def clean(self):
        """
        Delete all configurations in /etc/virt-who.conf.
        """
        os.system(f"echo '' > {self.local_file}")
        self.remote_ssh.put_file(self.local_file, self.remote_file)
        self.cfg = Configure(self.local_file, self.remote_ssh, self.remote_file)


def virtwho_ssh_connect(mode=None):
    """Define the ssh connection of virt-who host, get data from
    virtwho.ini file.
    :param mode: The test hypervisor mode.
    """
    virtwho = config.virtwho
    if mode == 'local':
        virtwho = config.local
    host = virtwho.server
    username = virtwho.username
    password = virtwho.password
    port = virtwho.port or 22
    return SSHConnect(host=host, user=username, pwd=password, port=port)


def get_register_handler(register_type):
    """Navigate to register type section in virtwho.ini.
    :param register_type: rhsm or satellite. rhsm as default.
    :return: register section
    """
    register = config.rhsm
    if register_type == 'satellite':
        register = config.satellite
    return register


def get_hypervisor_handler(mode):
    """Navigate to hypervisor mode section in virtwho.ini.
    :param mode: The hypervisor mode. esx as default
    :return: hypervisor section
    """
    hypervisor = config.esx
    if mode in ['xen', 'hyperv', 'rhevm', 'libvirt', 'kubevirt', 'ahv', 'local']:
        hypervisor = getattr(config, mode)
    return hypervisor
