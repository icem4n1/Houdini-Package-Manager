from __future__ import print_function

import json
import os

import hou

from .houdini_license import fullHoudiniLicenseName
from .package import Package, isPackage
from .package_status import fullPackageStatusName
from .setup_schema import makeSetupSchema


class NotPackageError(IOError):
    pass


class NotInstalledError(IOError):
    pass


class AlreadyInstalledError(IOError):
    pass


def isPackageFolder(path):
    if not os.path.isdir(path):
        return None
    return isPackage(os.listdir(path))


def packageNameFromContent(content_path):
    setup_file_path = os.path.join(content_path, 'package.setup')
    name = None
    if os.path.exists(setup_file_path) and os.path.isfile(setup_file_path):
        with open(setup_file_path) as file:
            data = json.load(file)
        name = data.get('name')
    if name is None:
        name = os.path.basename(content_path)
        if name.endswith('-master') and len(name) > 7:
            name = name[:-7]
        elif name.endswith('-dev') and len(name) > 4:
            name = name[:-4]
    return name


def packageAuthorFromContent(content_path):
    setup_file_path = os.path.join(content_path, 'package.setup')
    if os.path.exists(setup_file_path) and os.path.isfile(setup_file_path):
        with open(setup_file_path) as file:
            data = json.load(file)
        return data.get('author')


def findFiles(path, ignore_folders=True, recursive=False):
    for root, folders, files in os.walk(path):
        for file in files:
            yield os.path.join(root, file)
        if not ignore_folders:
            for folder in folders:
                yield os.path.join(root, folder)
        if not recursive:
            break


class LocalPackage(Package):
    def __init__(self, package_file):
        self.package_file = os.path.normpath(package_file).replace('\\', '/')

        if not os.path.isfile(package_file):
            raise IOError('File "{0}" not found'.format(package_file))

        with open(package_file) as file:
            data = json.load(file)

        self.content_path = os.path.normpath(hou.expandString(data['path'])).replace('\\', '/')
        if not os.path.isdir(self.content_path):
            raise IOError(self.content_path)

        if not isPackageFolder(self.content_path):
            raise NotPackageError('Folder "{0}" is not a package'.format(self.content_path))

        setup_file = os.path.join(self.content_path, 'package.setup')
        if os.path.isfile(setup_file):
            with open(setup_file) as file:
                data = json.load(file)
        else:
            data = {}
        self.name = data.get(u'name') or os.path.basename(self.content_path)
        self.description = data.get(u'description')
        self.source = data.get(u'source')
        self.source_type = data.get(u'source_type')
        self.author = data.get(u'author')
        self.version = data.get(u'version')
        self.version_type = data.get(u'version_type')
        self.hversion = data.get(u'hversion')
        self.hlicense = fullHoudiniLicenseName(data.get(u'hlicense'))
        self.status = fullPackageStatusName(data.get(u'status'))
        self.setup_schema = data.get(u'setup_schema')

    def files(self, extensions, root='', ignore_folders=True, recursive=False):
        if not os.path.isdir(self.content_path):
            raise hou.ObjectWasDeleted

        path = os.path.join(self.content_path, root)
        if not os.path.isdir(path):
            return ()

        file_list = []
        for file in findFiles(path, ignore_folders, recursive):
            if file.endswith(extensions):
                file_path = os.path.join(path, file)
                file_list.append(file_path)
        return tuple(file_list)

    def libraries(self):
        return self.files(('.otl', '.otlnc', '.otllc',
                           '.hda', '.hdanc', '.hdalc'),
                          root='otls',
                          ignore_folders=False)

    def shelves(self):
        return self.files('.shelf', 'toolbar')

    def panels(self):
        return self.files('.pypanel', 'python_panels')

    def isInstalled(self):
        return os.path.isfile(self.package_file)

    def isEnabled(self):
        try:
            with open(self.package_file, 'r') as file:
                data = json.load(file, encoding='utf-8')
                return data.get(u'enable', True)
        except IOError:
            return False  # Todo: raise NotInstalledError?

    def enable(self, enable=True):
        # Todo: check if not installed
        with open(self.package_file, 'r') as file:
            data = json.load(file)
        with open(self.package_file, 'w') as file:
            data[u'enable'] = enable
            json.dump(data, file, indent=4, encoding='utf-8')

    @staticmethod
    def install(content_path, enable=True, setup_schema=None):
        content_path = os.path.normpath(content_path).replace('\\', '/')

        if not os.path.exists(content_path) or not os.path.isdir(content_path):
            raise FileNotFoundError('Package folder not found')

        name = packageNameFromContent(content_path).replace(' ', '_')  # Todo: what if name missing
        author = packageAuthorFromContent(content_path)
        package_file_name = name + '.json'
        if author:
            package_file_name = author.replace(' ', '_') + '__' + package_file_name
        package_file = os.path.join(hou.expandString('$HOUDINI_USER_PREF_DIR/packages'), package_file_name)
        if os.path.exists(package_file):
            raise AlreadyInstalledError('Package already installed')

        setup_schema = setup_schema or makeSetupSchema(content_path)
        if not setup_schema:
            data = {
                u'enable': enable,
                u'path': content_path
            }
        else:
            package_root_path = os.path.join(content_path, setup_schema['root']).replace('\\', '/')
            data = {
                u'enable': enable,
                u'path': package_root_path,
                u'env': [
                    {name.upper(): package_root_path}
                ]
            }
            if 'hda_roots' in setup_schema and setup_schema['hda_roots']:
                hda_roots_vars = {u'HOUDINI_OTLSCAN_PATH': list(map(lambda r: '${0}/{1}'.format(name.upper(), r),
                                                                    setup_schema['hda_roots']))}
                data[u'env'].append(hda_roots_vars)
        with open(package_file, 'w') as file:
            json.dump(data, file, indent=4, encoding='utf-8')

    def uninstall(self):
        # Todo: optional remove package content folder
        os.remove(self.package_file)

    def __repr__(self):
        return 'Package(r"{0}")'.format(self.package_file)

    def __str__(self):
        return self.content_path


def findInstalledPackages():
    def jsonsFromFolderAlphabetical(path):
        if not os.path.isdir(path):
            return ()
        file_paths = []
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if file.endswith('.json') and os.path.isfile(file_path):
                file_paths.append(file_path)
        return sorted(file_paths)

    json_paths = []

    packages_path = hou.expandString('$HOUDINI_USER_PREF_DIR/packages')
    json_paths.extend(jsonsFromFolderAlphabetical(packages_path))

    packages_path = hou.expandString('$HFS/packages')
    json_paths.extend(jsonsFromFolderAlphabetical(packages_path))

    if hou.getenv('HSITE') is not None:
        major, minor, build = hou.applicationVersion()
        packages_path = hou.expandString('$HSITE/houdini{0}.{1}/packages'.format(major, minor))
        json_paths.extend(jsonsFromFolderAlphabetical(packages_path))

    if hou.getenv('HOUDINI_PACKAGE_DIR') is not None:
        packages_path = hou.expandString('$HOUDINI_PACKAGE_DIR')
        json_paths.extend(jsonsFromFolderAlphabetical(packages_path))

    # Todo: support dynamic setting of the package dir if possible

    packages = []
    for path in json_paths:
        try:
            package = LocalPackage(path)
            packages.append(package)
        except IOError:
            pass

    return tuple(packages)
