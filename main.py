import os
import sys
import json
import time
import subprocess

import psutil

MAC_CHROME_APP_NAMES = (
    'Google Chrome',
    'Google Chrome Canary',
    'Google Chrome Dev',
    'Google Chrome Beta',
)


def get_version_and_user_data_path():
    os_and_user_data_paths = {
        'win32': {
            'stable': '~/AppData/Local/Google/Chrome/User Data',
            'canary': '~/AppData/Local/Google/Chrome SxS/User Data',
            'dev': '~/AppData/Local/Google/Chrome Dev/User Data',
            'beta': '~/AppData/Local/Google/Chrome Beta/User Data',
        },
        'linux': {
            'stable': '~/.config/google-chrome',
            'canary': '~/.config/google-chrome-canary',
            'dev': '~/.config/google-chrome-unstable',
            'beta': '~/.config/google-chrome-beta',
        },
        'darwin': {
            'stable': '~/Library/Application Support/Google/Chrome',
            'canary': '~/Library/Application Support/Google/Chrome Canary',
            'dev': '~/Library/Application Support/Google/Chrome Dev',
            'beta': '~/Library/Application Support/Google/Chrome Beta',
        },
    }

    for platform, version_and_user_data_path in os_and_user_data_paths.items():
        available_version_and_user_data_path = {}
        if sys.platform.startswith(platform):
            for version, user_data_path in version_and_user_data_path.items():
                user_data_path = os.path.abspath(os.path.expanduser(user_data_path))
                if os.path.exists(user_data_path):
                    available_version_and_user_data_path[version] = user_data_path
            return available_version_and_user_data_path

    raise Exception('Unsupported platform %s' % sys.platform)


def is_target_chrome_process(process):
    process_name = process.name()
    if sys.platform == 'darwin':
        return process_name in MAC_CHROME_APP_NAMES

    if os.path.splitext(process_name)[0] != 'chrome':
        return False

    parent = process.parent()
    if parent is not None and parent.name() == process_name:
        return False

    return True


def collect_running_chromes():
    running_chromes = []
    for process in psutil.process_iter():
        try:
            if not process.is_running():
                continue
            if not is_target_chrome_process(process):
                continue
            running_chromes.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return running_chromes


def collect_executable_paths(processes):
    executable_paths = set()
    for process in processes:
        try:
            executable_paths.add(process.exe())
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return executable_paths


def wait_for_processes_to_exit(processes, timeout_seconds):
    deadline = time.time() + timeout_seconds
    remaining = processes
    while len(remaining) > 0 and time.time() < deadline:
        still_running = []
        for process in remaining:
            try:
                if process.is_running():
                    still_running.append(process)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        remaining = still_running
        if len(remaining) > 0:
            time.sleep(0.2)
    return remaining


def gracefully_quit_chrome_on_mac(running_chromes):
    app_names = set()
    for process in running_chromes:
        try:
            process_name = process.name()
            if process_name in MAC_CHROME_APP_NAMES:
                app_names.add(process_name)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    for app_name in app_names:
        applescript = f'tell application "{app_name}" to quit'
        subprocess.run(
            ['osascript', '-e', applescript],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def terminate_processes(processes):
    for process in processes:
        try:
            if process.is_running():
                process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def kill_processes(processes):
    for process in processes:
        try:
            if process.is_running():
                process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def shutdown_chrome():
    running_chromes = collect_running_chromes()
    if len(running_chromes) == 0:
        return set()

    terminated_chromes = collect_executable_paths(running_chromes)

    if sys.platform == 'darwin':
        gracefully_quit_chrome_on_mac(running_chromes)
        running_chromes = wait_for_processes_to_exit(running_chromes, timeout_seconds=10)

    if len(running_chromes) > 0:
        terminate_processes(running_chromes)
        running_chromes = wait_for_processes_to_exit(running_chromes, timeout_seconds=5)

    if len(running_chromes) > 0:
        kill_processes(running_chromes)

    return terminated_chromes


def get_macos_app_bundle(executable_path):
    marker = '.app/Contents/MacOS/'
    if marker not in executable_path:
        return None
    return executable_path.split(marker)[0] + '.app'


def restart_chrome(terminated_chromes):
    for chrome in terminated_chromes:
        try:
            if sys.platform == 'darwin':
                app_bundle = get_macos_app_bundle(chrome)
                if app_bundle is not None and os.path.exists(app_bundle):
                    subprocess.Popen(['open', '-a', app_bundle], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    continue
            subprocess.Popen([chrome], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            print('Failed to restart Chrome executable', chrome)


def get_last_version(user_data_path):
    last_version_file = os.path.join(user_data_path, 'Last Version')
    if not os.path.exists(last_version_file):
        return None
    with open(last_version_file, 'r', encoding='utf-8') as fp:
        return fp.read()


def set_all_is_glic_eligible(obj):
    """Recursively find and set all is_glic_eligible to true."""
    modified = False
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'is_glic_eligible' and value != True:
                obj[key] = True
                modified = True
            elif isinstance(value, (dict, list)):
                if set_all_is_glic_eligible(value):
                    modified = True
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                if set_all_is_glic_eligible(item):
                    modified = True
    return modified


def patch_local_state(user_data_path, last_version):
    local_state_file = os.path.join(user_data_path, 'Local State')
    if not os.path.exists(local_state_file):
        print('Failed to patch Local State. File not found', local_state_file)
        return

    with open(local_state_file, 'r', encoding='utf-8') as fp:
        local_state = json.load(fp)

    modified = False

    # 1. Set all is_glic_eligible to true (recursive)
    if set_all_is_glic_eligible(local_state):
        modified = True
        print('Patched is_glic_eligible')

    # 2. Set variations_country to "us" (root level)
    if local_state.get('variations_country') != 'us':
        local_state['variations_country'] = 'us'
        modified = True
        print('Patched variations_country')

    # 3. Set variations_permanent_consistency_country[0] to last_version, [1] to "us" (root level)
    if 'variations_permanent_consistency_country' in local_state:
        if isinstance(local_state['variations_permanent_consistency_country'], list) and \
           len(local_state['variations_permanent_consistency_country']) >= 2:
            if local_state['variations_permanent_consistency_country'][0] != last_version or \
               local_state['variations_permanent_consistency_country'][1] != 'us':
                local_state['variations_permanent_consistency_country'][0] = last_version
                local_state['variations_permanent_consistency_country'][1] = 'us'
                modified = True
                print('Patched variations_permanent_consistency_country')

    if modified:
        with open(local_state_file, 'w', encoding='utf-8') as fp:
            json.dump(local_state, fp)
        print('Succeeded in patching Local State')
    else:
        print('No need to patch Local State')


def main():
    version_and_user_data_path = get_version_and_user_data_path()
    if len(version_and_user_data_path) == 0:
        raise Exception('No available user data path found')

    terminated_chromes = shutdown_chrome()
    if len(terminated_chromes) > 0:
        print('Shutdown Chrome')

    for version, user_data_path in version_and_user_data_path.items():
        last_version = get_last_version(user_data_path)
        if last_version is None:
            print('Failed to get version. File not found', os.path.join(user_data_path, 'Last Version'))
            continue
        print('Patching Chrome', version, last_version, '"'+user_data_path+'"')
        patch_local_state(user_data_path, last_version)

    if len(terminated_chromes) > 0:
        print('Restart Chrome')
        restart_chrome(terminated_chromes)

    input('Enter to continue...')


if __name__ == '__main__':
    main()
