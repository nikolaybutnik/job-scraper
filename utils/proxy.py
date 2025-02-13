import os
import requests, re
from bs4 import BeautifulSoup

# TODO: Find a way to validate proxies and compile a valid list


def clear_used_proxies():
    filename = "proxy_store/used_proxies.txt"
    if os.path.exists(filename):
        os.remove(filename)


def generate_proxy_list():
    clear_used_proxies()

    regex = r"[0-9]+(?:\.[0-9]+){3}:[0-9]+"
    filename = "proxy_store/proxies_list.txt"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    c = requests.get("https://spys.me/proxy.txt")
    test_str = c.text
    a = re.finditer(regex, test_str, re.MULTILINE)
    with open(filename, "w") as file:
        for i in a:
            print(i.group(), file=file)

    d = requests.get("https://free-proxy-list.net/")
    soup = BeautifulSoup(d.content, "html.parser")
    td_elements = soup.select(".fpl-list .table tbody tr td")
    ips = []
    ports = []
    for j in range(0, len(td_elements), 8):
        ips.append(td_elements[j].text.strip())
        ports.append(td_elements[j + 1].text.strip())
    with open(filename, "a") as myfile:
        for ip, port in zip(ips, ports):
            proxy = f"{ip}:{port}"
            print(proxy, file=myfile)


def get_proxy():
    proxies_list = "proxy_store/proxies_list.txt"
    used_proxies_list = "proxy_store/used_proxies.txt"

    # Generate initial proxy list if missing
    if not os.path.exists(proxies_list):
        generate_proxy_list()

    with open(proxies_list, "r+") as proxies_list_file:
        available_proxies = proxies_list_file.readlines()

        # Regenerate if empty after initial check
        if not available_proxies:
            generate_proxy_list()
            proxies_list_file.seek(0)
            available_proxies = proxies_list_file.readlines()

        if available_proxies:
            last_proxy = available_proxies[-1].strip()

            # Write to used proxies
            with open(used_proxies_list, "a") as used_file:
                used_file.write(last_proxy + "\n")

            # Remove last proxy from original file
            proxies_list_file.seek(0)
            proxies_list_file.writelines(available_proxies[:-1])
            proxies_list_file.truncate()

            return "http://" + last_proxy
        return None
