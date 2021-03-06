# sys
import subprocess
import json
import re
from pathlib import Path
from dataclasses import dataclass

# 3rd
from see import Hook


@dataclass
class ChecksecFile:
    relro: bool
    canary: bool
    nx: bool
    pie: str
    rpath: bool
    runpath: bool
    symtables: bool
    fortify_source: bool
    fortified: bool
    fortifyable: bool


class SecurityHook(Hook):

    CHECKSEC_BIN = Path(__file__).parent.parent / "tools" / "checksec" / "checksec"

    def __init__(self, parameters):
        super().__init__(parameters)

        if not self.CHECKSEC_BIN.exists():
            raise RuntimeError('Cannot find checksec, did you forget to init the submodule ?')
        self.checksec = str(self.CHECKSEC_BIN)

        self.context.subscribe('filesystem_new_file', self.check_file)

    def check_file(self, event):
        # event args
        inode = event.inode

        mime = event.mime_type
        filepath = event.str_path
        if re.match(r'application/x(-pie)?-(executable|sharedlib)', mime):
            # run checksec and load json
            cmdline = [self.checksec, '--output', 'json', '--file', filepath]
            checksec_data = json.loads(subprocess.check_output(cmdline).decode())
            profile = checksec_data['file']
            self.logger.debug('profile: %s', profile)

            def str2bool(string):
                return string.lower() in ['yes', 'true', 'y', '1']

            relro = True if profile['relro'] in ["full", "partial"] else False
            canary = str2bool(profile['canary'])
            nx = str2bool(profile['nx'])
            pie = profile['pie']
            rpath = str2bool(profile['rpath'])
            runpath = str2bool(profile['runpath'])
            symtables = str2bool(profile['symtables'])
            fortify_source = str2bool(profile['fortify_source'])
            fortified = profile['fortified']
            fortifyable = profile['fortify-able']

            checksec_file = ChecksecFile(relro, canary, nx, pie, rpath, runpath,
                                         symtables, fortify_source, fortified, fortifyable)
            self.context.trigger('security_checksec_bin', inode=inode, checksec_file=checksec_file)
