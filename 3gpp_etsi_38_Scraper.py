import requests
from bs4 import BeautifulSoup
import re
import os

# ===================== Config =====================
# 定义BASE_URL为空，后续根据选择项确定所选series地址
BASE_URL = ""
# 定义基础URL字典：键是数字选项，值是对应URL
URLs = {
        "1" : "https://www.etsi.org/deliver/etsi_ts/138100_138199/",
        "2" : "https://www.etsi.org/deliver/etsi_ts/138200_138299/",
        "3" : "https://www.etsi.org/deliver/etsi_ts/138300_138399/"
       }

SAVE_ROOT = "./38_series"
CHUNK_SIZE = 8192

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}
# ==================================================

def get_soup(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def get_3gpp_38_series_list():
    print("\nFetching 38 series document list...\n")
    soup = get_soup(BASE_URL)
    if not soup:
        return []

    series = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip("/")
        # 从完整路径中提取最后一段 138xxx
        folder_name = href.split("/")[-1]
        if re.match(r'^138\d{3}$', folder_name):
            series.append(folder_name)

    return sorted(series)

def get_versions(ts_num):
    url = BASE_URL + ts_num + "/"
    soup = get_soup(url)
    if not soup:
        return []

    versions = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # 从完整路径中提取最后一段版本号 19.02.00_60
        folder_name = href.split("/")[-2]
        match = re.match(r'\d{2}.\d{2}.\d{2}_60', folder_name)
        if match:
            versions.append((match.group(0), href))
            
    return sorted(versions, reverse=True)

def download_pdf(ts_num, version_str):
    save_dir = os.path.join(SAVE_ROOT, f"TS_{ts_num}")
    os.makedirs(save_dir, exist_ok=True)

    base_url = BASE_URL + ts_num + "/" + version_str
    soup = get_soup(base_url)
    if not soup:
        print("Failed to access version directory.")
        return

    pdf_name = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".pdf") and ts_num in href:
            pdf_name = href.split("/")[-1]
            break

    if not pdf_name:
        print(f"PDF file '{pdf_name}' not found.\n")
        return

    download_url = base_url + "/" + pdf_name
    save_path = os.path.join(save_dir, pdf_name)

    print(f"Starting download: {download_url}")
    try:
        with requests.get(download_url, headers=HEADERS, stream=True, timeout=50) as r:
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
                    print(".", end="", flush=True)
        print(f"\nDownload completed successfully!")
        print(f"File saved to: {save_path}\n")
    except Exception as e:
        print(f"Download failed: {e}")

def main():
    print("=" * 60)
    print("      ETSI 3GPP 38 Series Downloader (Menu Mode)")
    print("=" * 60)

    # 打印所有可选的URL列表
    print("The series to be selected are listed below:")
    for key, url in URLs.items():
        print(f"{key}: {url}")

    # 循环获取用户输入，直到输入有效
    while True:
        try:
            choice_series = input("\nEnter the nuember of the serie to download：")
            # 判断输入是否在字典的键中
            if choice_series in URLs:  # TODO: or choice_series == 0: download all series 
                break
            else:
                print(f"Invalid input. Please enter a valid number: 0 ~ {len(URLs)} ")
        except:
            print(f"Invalid input. Please enter a valid number: 0 ~ {len(URLs)}")

    global SAVE_ROOT
    SAVE_ROOT = SAVE_ROOT + f"_{choice_series}00_series"

    # 获取选中的URL
    global BASE_URL
    BASE_URL = URLs[choice_series]

    series_list = get_3gpp_38_series_list()
    if not series_list:
        print("Failed to retrieve document list.")
        return

    print("Available 38 Series Documents:")
    print(f"  {0:2d}. All ts")
    for i, ts in enumerate(series_list, 1):
        print(f"  {i:2d}. {ts}")

    while True:
        try:
            choice = int(input("\nEnter the number of the document to download: "))
            if 0 <= choice <= len(series_list):
                break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    nrOfChoice = 1
    v_choice = 0
    ts_start_index = 0
    # 0: select all the ts then only download the latest version (v_choice=1) for each ts.
    if choice == 0:
        nrOfChoice = len(series_list)
        ts_start_index = 0
        v_choice = 1  # only download the latest one, no need to choose 
    else: # !0: select the specific ts whose index is choice-1
        ts_start_index = choice - 1

    # iterate the choosed ts for both choice 0 and !0
    for i in range(0, nrOfChoice):
        print(f"{i}. >>>>>>> choice:{choice}, nrOfChoice:{nrOfChoice}, ts_start_index:{ts_start_index}, v_choice:{v_choice}")
        selected_ts = series_list[ts_start_index]
        version_list = get_versions(selected_ts)      
        if not version_list:
            print("No versions found for this document.")
            return
            
        if v_choice == 0:  # v_choice:0 means no version selected, let user select a version
            print("\nAvailable versions (newest first):")
            for j, (ver, _) in enumerate(version_list, 1):
                print(f"  {j:2d}. {ver}")

            while True:
                try:
                    v_choice = int(input("\nEnter the number of the version to download: "))
                    if 1 <= v_choice <= len(version_list):
                        break
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

        ver_selected, href_selected = version_list[v_choice - 1]
        print(f"\nDownloading: {selected_ts} (Version: {ver_selected}) (href: {href_selected})")
        download_pdf(selected_ts, ver_selected)
        ts_start_index += 1

if __name__ == "__main__":
    main()