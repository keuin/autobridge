import logging
import re
import telnetlib

import requests


def enable_telnet() -> bool:
    r = requests.get('http://192.168.1.1:8080/cgi-bin/telnetenable.cgi?telnetenable=1')
    return r.ok and 'if (1 == 1)' in r.text


def set_bridge_mode(password: str):
    logging.info("Connecting to telnet server...")
    with telnetlib.Telnet('192.168.1.1') as tel:
        logging.info("Waiting for login prompt...")
        try:
            tel.read_until(b'Login:')
        except EOFError as e:
            logging.error(f"Connection closed unexpectedly. ({e}) "
                          "Note that some routers forbid multiple concurrent sessions. "
                          "Please logout and retry if you have logged in manually.")
            return False
        logging.info("Entering username...")
        tel.write(b'root\r\n')
        tel.read_until(b'Password:')
        logging.info("Entering password...")
        tel.write(password.encode('ascii') + b'\r\n')
        logging.info("Spawning shell...")
        tel.read_until(b'#')
        logging.info("Finding PPPoE credential...")
        tel.write(b"cat /flash/cfg/agentconf/param.xml | grep -E 'dev_WANPPP_Username|dev_WANPPP_Password'\r\n")
        tel.read_until(b'\r\n')
        config = tel.read_until(b'\r\n#').decode('ascii')
        pppoe_password_found, pppoe_username_found = False, False
        for ln in config.split('\r\n'):
            if 'value="NULL"' in ln or 'value=""' in ln:
                continue
            if 'dev_WANPPP_Password' in ln:
                r = re.findall(r'value="(.+)"', ln)
                if not r:
                    continue
                logging.info(f'[+] Possible PPPoE password: {r[0]}')
                pppoe_password_found = True
            if 'dev_WANPPP_Username' in ln:
                r = re.findall(r'value="(.+)"', ln)
                if not r:
                    continue
                logging.info(f'[+] Possible PPPoE username: {r[0]}')
                pppoe_username_found = True
        if not pppoe_password_found and not pppoe_username_found:
            logging.error("Cannot detect PPPoE credential. "
                          "Please make sure you have the correct username and password to dial up.")
            if input('Proceed? (y/N)').strip().lower() != 'y':
                return False
        logging.info("Detecting `inter_web`...")
        tel.write(b'/rom/fhbin/inter_web\r\n')
        tel.read_until(b'\n')
        if b'Usage : inter_web (get|set|attri) seq [val]' not in (resp := tel.read_until(b'\n')):
            logging.error(f"Cannot find executable `inter_web`: {resp.decode('ascii')}")
            return False
        logging.info('Found valid `inter_web`.')
        logging.info('Probing account setting entry ID...')
        tel.write(b'cat > /tmp/a.sh\r\n')
        with open('set_bridge_mode.sh', 'r', encoding='ascii') as f:
            lines = list(f)
            for i, ln in enumerate(lines):
                logging.info(f'Writing lines ({i + 1}/{len(lines)})...')
                tel.write(ln.rstrip().encode('ascii') + b'\r\n')
        tel.write(b'\x04')  # Ctrl-D
        logging.info('Executing probe script...')
        tel.write(b'/bin/sh /tmp/a.sh; rm /tmp/a.sh\r\n')
        tel.read_until(b'CONNTYPE=')
        tel.read_until(b'CONNTYPE=')
        connection_type = tel.read_until(b'\r\n').decode('ascii').strip()
        if connection_type.isdigit():
            logging.info(f'PPPC_ConnectionType = {connection_type}')
        else:
            logging.error(f'Invalid PPPC_ConnectionType: {connection_type}')
            return False
        tel.write(b'/rom/fhbin/inter_web get ' + connection_type.encode('ascii') + b'\r\n')
        tel.read_until(b'\r\n')
        tel.read_until(b'\r\n')
        mode = tel.read_until(b'\r\n').strip().decode('ascii')
        if 'PPPoE_Bridged' in mode:
            logging.info('Your router is already set to BRIDGE mode. No actions needed.')
            return True
        elif 'IP_Routed' in mode:
            logging.info('Your router is working in ROUTE mode.')
        else:
            logging.info(f'Unexpected mode `{mode}`. Cannot proceed on.')
            return False
        logging.info("Switching to BRIDGE mode...")
        tel.write(b'/rom/fhbin/inter_web set ' + connection_type.encode('ascii') +
                  b' "PPPoE_Bridged" && reboot\r\n')
        logging.info("Waiting for the router to reboot...")
        try:
            tel.read_all()
        except IOError:
            pass
        logging.info("Congratulations! After rebooting your router, "
                     "please set your secondary router to PPPoE dial-up mode. "
                     "If you don't have the correct PPPoE username/password, please consult your ISP.")
        return True


def main():
    telnet_password = None
    while not telnet_password:
        telnet_password = input("Your router's Telnet password:").strip()
    logging.info('Enabling telnet server...')
    if not enable_telnet():
        logging.critical('Failed to enable telnet server. Your router may be incompatible with this script.')
        exit(1)
    else:
        logging.info('Telnet server is enabled.')
    exit(0 if set_bridge_mode(telnet_password) else 1)


if __name__ == '__main__':
    logging.basicConfig(format='[%(levelname)s] %(message)s')
    logging.root.setLevel(logging.INFO)
    main()
